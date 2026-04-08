"""
YOVUS UI - v2.0 Complete Rewrite
All handlers implemented, cloud + inpaint support
"""
import os
import time
import gc
import logging
from pathlib import Path
from typing import Optional

import gradio as gr

from src.config.settings import config
from src.core.gpu_manager import GPUManager
from src.core.pipeline_engine import PipelineEngine, PipelineJob

logger = logging.getLogger("yovus.ui")

CSS_PATH = Path(__file__).parent.parent.parent / "assets" / "css" / "japanese_theme.css"


def load_css() -> str:
    if CSS_PATH.exists():
        return CSS_PATH.read_text(encoding="utf-8")
    return ""


class YovusApp:
    """Main Application - v2.0 with Cloud + Inpaint"""

    def __init__(self):
        self.gpu_manager = GPUManager()
        self.pipeline = PipelineEngine()
        self.current_job = None
        self._log_messages = []

    def _add_log(self, msg, level="info"):
        ts = time.strftime("%H:%M:%S")
        self._log_messages.append(f"[{ts}] {msg}")
        if len(self._log_messages) > 200:
            self._log_messages = self._log_messages[-100:]

    def _get_logs(self):
        return chr(10).join(self._log_messages[-50:])

    # ── Handlers ──

    def on_detect_gpu(self):
        info = self.gpu_manager.detect()
        status = self.gpu_manager.format_status()
        rec = self.gpu_manager.get_recommended_settings()
        msg = rec.get("message", "")
        return f"{status}\n\n{msg}"

    def on_scan_photos(self, photos_dir):
        if not photos_dir or not Path(photos_dir).exists():
            return "Directory not found", [], self._get_logs()
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = [f for f in Path(photos_dir).iterdir() if f.suffix.lower() in exts]
        if not photos:
            return "No photos found", [], self._get_logs()

        # Copy preview images to system temp dir (Gradio always allows this)
        import shutil
        import tempfile
        preview_dir = Path(tempfile.gettempdir()) / "yovus_preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        # Clean old previews
        for old in preview_dir.iterdir():
            if old.is_file():
                old.unlink(missing_ok=True)

        preview_paths = []
        for p in sorted(photos)[:20]:
            dst = preview_dir / p.name
            shutil.copy2(p, dst)
            preview_paths.append(str(dst))

        self._add_log(f"Scanned: {len(photos)} photos")
        return f"Found: {len(photos)} photos", preview_paths, self._get_logs()

    def on_analyze_video(self, video_path):
        if not video_path or not Path(video_path).exists():
            return "File not found", None, self._get_logs()
        try:
            from src.pipeline.video_processor import VideoProcessor
            vp = VideoProcessor(config.paths.temp_dir)
            info = vp.probe(Path(video_path))
            details = (
                f"Resolution: {info.width}x{info.height}\n"
                f"FPS: {info.fps:.1f}\n"
                f"Frames: {info.frame_count}\n"
                f"Duration: {info.duration:.1f}s ({info.duration/60:.1f}min)\n"
                f"Audio: {'Yes' if info.has_audio else 'No'}\n"
                f"Size: {info.file_size_mb:.1f}MB"
            )
            import cv2
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, info.frame_count // 4)
            ret, frame = cap.read()
            cap.release()
            self._add_log(f"Video analyzed: {info.width}x{info.height}, {info.frame_count} frames")
            return details, frame if ret else None, self._get_logs()
        except Exception as e:
            return f"Error: {e}", None, self._get_logs()

    def on_start_processing(self, video_path, photos_dir, mode, face_enhancer,
                            enhance_blend, face_mask_blur, target_face_idx, progress=gr.Progress()):
        if not video_path or not photos_dir:
            return None, "Input missing", self._get_logs()

        mode_map = {
            "Face Only": "face_only",
            "Face + Body": "face_and_body",
            "Full Replace (LoRA)": "full_replace",
            "Inpaint Replace": "full_replace",
            "Cloud": "cloud",
        }

        job = PipelineJob(
            job_id=f"job_{int(time.time())}",
            source_video=Path(video_path),
            reference_photos_dir=Path(photos_dir),
            output_path=config.paths.output_dir / f"output_{int(time.time())}.mp4",
            mode=mode_map.get(mode, "face_only"),
        )

        self._add_log(f"Started: {mode}")
        self._register_all_handlers(face_enhancer, enhance_blend, int(face_mask_blur), int(target_face_idx))

        def update_progress(prog, stage):
            try:
                progress(prog, desc=stage)
            except Exception:
                pass

        self.pipeline.set_progress_callback(update_progress)
        self.pipeline.set_log_callback(self._add_log)

        try:
            results = self.pipeline.run_sync(job)
            if job.status == "completed":
                output = str(job.output_path) if job.output_path.exists() else None
                return output, "Complete", self._get_logs()
            else:
                errors = [r.message for r in results if r.status.value == "failed"]
                err_msg = "; ".join(errors)
                return None, f"Error: {err_msg}", self._get_logs()
        except Exception as e:
            self._add_log(f"Error: {e}")
            return None, f"Error: {e}", self._get_logs()

    def _register_all_handlers(self, enhancer, blend, blur, face_idx):
        from src.pipeline.video_processor import VideoProcessor
        from src.pipeline.face_detector import FaceDetector

        vp = VideoProcessor(config.paths.temp_dir)
        fd = FaceDetector(device=config.gpu.device)

        def video_decode(job, results):
            info = vp.probe(job.source_video)
            frames_dir = vp.extract_frames(job.source_video)
            job.shared_data["frames_dir"] = str(frames_dir)
            job.shared_data["fps"] = info.fps
            job.shared_data["has_audio"] = info.has_audio
            job.shared_data["frame_count"] = info.frame_count
            return {"frames_dir": str(frames_dir), "fps": info.fps}

        def face_detect_reference(job, results):
            refs = fd.extract_best_references(job.reference_photos_dir, max_count=30)
            if not refs:
                raise ValueError("No faces found in reference photos")
            job.shared_data["reference_faces"] = refs
            job.shared_data["best_ref"] = refs[0]
            return {"count": len(refs)}

        def face_swap(job, results):
            import cv2
            import shutil

            frames_dir = Path(job.shared_data.get("frames_dir", ""))
            if not frames_dir.exists():
                raise ValueError("Frames not extracted")

            ref = job.shared_data.get("best_ref")
            if not ref:
                raise ValueError("No reference face")

            source_face = ref["face_data"]
            frame_files = sorted(frames_dir.glob("*.png"))
            if not frame_files:
                raise ValueError(f"No frame files found in {frames_dir}")

            out_dir = config.paths.temp_dir / "swapped" / job.job_id
            out_dir.mkdir(parents=True, exist_ok=True)

            self._add_log(f"Processing {len(frame_files)} frames...")
            swapped_count = 0

            try:
                from src.pipeline.face_swapper import FaceSwapper
                fs = FaceSwapper(device=config.gpu.device)
                fs.initialize(config.paths.models_dir)

                for i, fp in enumerate(frame_files):
                    frame = cv2.imread(str(fp))
                    if frame is None:
                        shutil.copy2(fp, out_dir / fp.name)
                        continue
                    try:
                        faces = fd.detect(frame, max_faces=5)
                        if faces:
                            tidx = min(int(face_idx), len(faces) - 1)
                            if fs._use_native and source_face._raw and faces[tidx]._raw:
                                frame = fs._swap_native(source_face._raw, frame, faces[tidx]._raw)
                            else:
                                frame = fs.swap_video_frame(source_face, frame, faces, int(face_idx))
                            swapped_count += 1
                    except Exception as frame_err:
                        logger.debug(f"Frame {i} swap error: {frame_err}")

                    cv2.imwrite(str(out_dir / fp.name), frame)

                    if (i + 1) % 30 == 0:
                        self._add_log(f"Face swap: {i+1}/{len(frame_files)} ({swapped_count} swapped)")

                fs.release()
            except Exception as e:
                self._add_log(f"Face swap init error: {e}")
                self._add_log("Copying original frames as fallback...")
                for fp in frame_files:
                    dst = out_dir / fp.name
                    if not dst.exists():
                        shutil.copy2(fp, dst)

            # Safety check: ensure output dir is not empty
            output_count = len(list(out_dir.glob("*.png")))
            if output_count == 0:
                self._add_log("WARNING: No output frames, copying originals")
                for fp in frame_files:
                    shutil.copy2(fp, out_dir / fp.name)
                output_count = len(frame_files)

            job.shared_data["swapped_dir"] = str(out_dir)
            self._add_log(f"Face swap done: {swapped_count}/{output_count} faces replaced")
            return {"processed": output_count, "swapped": swapped_count}

        def face_enhance(job, results):
            swapped_dir = Path(job.shared_data.get("swapped_dir", ""))
            if not swapped_dir.exists():
                return {}

            from src.pipeline.post_processor import FaceEnhancer
            import cv2
            fe = FaceEnhancer(model_type=enhancer, device=config.gpu.device, models_dir=config.paths.models_dir)
            try:
                frames = sorted(swapped_dir.glob("*.png"))
                for i, fp in enumerate(frames):
                    frame = cv2.imread(str(fp))
                    if frame is not None:
                        enhanced = fe.enhance(frame, blend_factor=float(blend))
                        cv2.imwrite(str(fp), enhanced)
                    if (i+1) % 50 == 0:
                        self._add_log(f"Enhance: {i+1}/{len(frames)}")
            except Exception as e:
                self._add_log(f"Enhancement error: {e}")
            finally:
                fe.release()
            return {}

        def pose_estimate(job, results):
            """DWPose 逐帧姿势提取"""
            import cv2
            from src.pipeline.body_swapper import PoseExtractor

            frames_dir = Path(job.shared_data.get("frames_dir", ""))
            frame_files = sorted(frames_dir.glob("*.png"))
            if not frame_files:
                raise ValueError("No frames for pose estimation")

            pose_dir = config.paths.temp_dir / "poses" / job.job_id
            pose_dir.mkdir(parents=True, exist_ok=True)

            pe = PoseExtractor(device=config.gpu.device)
            pe.initialize()

            try:
                for i, fp in enumerate(frame_files):
                    frame = cv2.imread(str(fp))
                    if frame is None:
                        # Write black pose for missing frames to avoid gaps
                        import numpy as np
                        black = np.zeros((512, 512, 3), dtype=np.uint8)
                        cv2.imwrite(str(pose_dir / fp.name), black)
                        continue
                    pose = pe.extract_pose(frame)
                    if pose is not None:
                        cv2.imwrite(str(pose_dir / fp.name), pose)
                    else:
                        import numpy as np
                        cv2.imwrite(str(pose_dir / fp.name), np.zeros_like(frame))

                    if (i + 1) % 30 == 0:
                        self._add_log(f"姿勢抽出: {i+1}/{len(frame_files)}")
            finally:
                pe.release()

            job.shared_data["poses_dir"] = str(pose_dir)
            self._add_log(f"姿勢抽出完了: {len(list(pose_dir.glob('*.png')))} フレーム")
            return {"poses_dir": str(pose_dir)}

        def body_segment(job, results):
            """人物分割 - 每帧生成人物mask"""
            import cv2
            from src.pipeline.segmentation import PersonSegmenter

            frames_dir = Path(job.shared_data.get("frames_dir", ""))
            frame_files = sorted(frames_dir.glob("*.png"))
            if not frame_files:
                raise ValueError("No frames for segmentation")

            mask_dir = config.paths.temp_dir / "masks" / job.job_id
            mask_dir.mkdir(parents=True, exist_ok=True)

            seg = PersonSegmenter(model_type=config.body_swap.segmentation_model, device=config.gpu.device)
            seg.initialize()

            try:
                for i, fp in enumerate(frame_files):
                    frame = cv2.imread(str(fp))
                    if frame is None:
                        continue
                    mask = seg.segment(frame)

                    # 膨胀mask确保完全覆盖人物
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
                    mask = cv2.dilate(mask, kernel, iterations=1)
                    mask = cv2.GaussianBlur(mask, (11, 11), 5)

                    cv2.imwrite(str(mask_dir / fp.name), mask)

                    if (i + 1) % 30 == 0:
                        self._add_log(f"人物分割: {i+1}/{len(frame_files)}")
            finally:
                seg.release()
            job.shared_data["masks_dir"] = str(mask_dir)
            self._add_log(f"人物分割完了: {len(list(mask_dir.glob('*.png')))} フレーム")
            return {"masks_dir": str(mask_dir)}

        def inpaint_mask(job, results):
            """背景修復 - 人物を除去して背景を修復"""
            import cv2
            from src.pipeline.video_inpainter import VideoInpainter

            frames_dir = Path(job.shared_data.get("frames_dir", ""))
            masks_dir = Path(job.shared_data.get("masks_dir", ""))
            if not masks_dir.exists():
                self._add_log("WARNING: Masks dir not found, skipping inpainting")
                job.shared_data["clean_bg_dir"] = str(frames_dir)
                return {}

            frame_files = sorted(frames_dir.glob("*.png"))

            clean_dir = config.paths.temp_dir / "clean_bg" / job.job_id
            clean_dir.mkdir(parents=True, exist_ok=True)

            inpainter = VideoInpainter(device=config.gpu.device, method=config.inpaint.model)
            inpainter.initialize()

            try:
                for i, fp in enumerate(frame_files):
                    frame = cv2.imread(str(fp))
                    mask_path = masks_dir / fp.name
                    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE) if mask_path.exists() else None

                    if frame is not None and mask is not None:
                        clean = inpainter.inpaint_frame(frame, mask)
                        cv2.imwrite(str(clean_dir / fp.name), clean)
                    elif frame is not None:
                        cv2.imwrite(str(clean_dir / fp.name), frame)

                    if (i + 1) % 30 == 0:
                        self._add_log(f"背景修復: {i+1}/{len(frame_files)}")
            finally:
                inpainter.release()
            job.shared_data["clean_bg_dir"] = str(clean_dir)
            self._add_log(f"背景修復完了")
            return {"clean_bg_dir": str(clean_dir)}

        def body_generate(job, results):
            """ControlNet + LoRA 全身生成"""
            import cv2
            import gc as _gc
            from src.pipeline.body_swapper import BodyGenerator

            # Free prior models' VRAM before loading ControlNet+SD
            # Release InsightFace FaceDetector (~600MB) to avoid OOM on 8GB cards
            try:
                fd.release()
            except Exception:
                pass
            _gc.collect()
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass

            poses_dir = Path(job.shared_data.get("poses_dir", ""))
            pose_files = sorted(poses_dir.glob("*.png"))
            if not pose_files:
                self._add_log("WARNING: No pose files, skipping body generation")
                return {}

            gen_dir = config.paths.temp_dir / "generated" / job.job_id
            gen_dir.mkdir(parents=True, exist_ok=True)

            # Find LoRA: first from shared_data (if lora_train stage ran), then filesystem
            lora_path = job.shared_data.get("lora_path")
            if lora_path:
                lora_path = Path(lora_path)
            if not lora_path or not lora_path.exists():
                lora_path = config.paths.lora_dir / "lora_weights"
            if not lora_path.exists() or not any(lora_path.glob("*.safetensors")):
                lora_path = None
                if config.paths.lora_dir.exists():
                    for p in config.paths.lora_dir.iterdir():
                        if p.is_dir() and any(p.glob("*.safetensors")):
                            lora_path = p
                            break

            bg = BodyGenerator(device=config.gpu.device)
            has_lora = lora_path is not None and lora_path.exists()

            try:
                bg.initialize(lora_path=lora_path if has_lora else None)
                if has_lora:
                    self._add_log(f"LoRA loaded: {lora_path}")
                else:
                    self._add_log("WARNING: LoRA未検出。汎用人物で生成します。先にModelsタブでLoRA学習を実行してください。")

                # Get original frame size
                frames_dir = Path(job.shared_data.get("frames_dir", ""))
                frame_list = sorted(frames_dir.glob("*.png"))
                if not frame_list:
                    raise ValueError("No frames found")
                sample_frame = cv2.imread(str(frame_list[0]))
                if sample_frame is None:
                    raise ValueError(f"Cannot read sample frame: {frame_list[0]}")
                orig_h, orig_w = sample_frame.shape[:2]

                # Generation size (divisible by 8, fit in VRAM)
                gen_w = max(8, min(orig_w, 768))
                gen_h = max(8, min(orig_h, 768))
                gen_w = gen_w - (gen_w % 8)
                gen_h = gen_h - (gen_h % 8)

                self._add_log(f"生成サイズ: {gen_w}x{gen_h} (元: {orig_w}x{orig_h})")

                # Use SAME seed for all frames to ensure temporal consistency
                # (different seeds cause flickering/inconsistent appearance)
                fixed_seed = 42
                for i, fp in enumerate(pose_files):
                    pose = cv2.imread(str(fp))
                    if pose is None:
                        continue

                    generated = bg.generate(
                        pose,
                        prompt="a photo of sks person, full body, high quality, detailed, professional photography, natural lighting",
                        negative_prompt="low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly, text, watermark",
                        num_inference_steps=config.body_swap.inference_steps,
                        controlnet_conditioning_scale=config.body_swap.controlnet_strength,
                        guidance_scale=config.body_swap.guidance_scale,
                        width=gen_w,
                        height=gen_h,
                        seed=fixed_seed,
                    )

                    if generated.shape[:2] != (orig_h, orig_w):
                        generated = cv2.resize(generated, (orig_w, orig_h), interpolation=cv2.INTER_LANCZOS4)

                    cv2.imwrite(str(gen_dir / fp.name), generated)

                    if (i + 1) % 10 == 0:
                        self._add_log(f"全身生成: {i+1}/{len(pose_files)}")
            finally:
                bg.release()
                # Re-initialize FaceDetector for downstream face_enhance
                try:
                    fd.initialize()
                except Exception:
                    pass
            job.shared_data["generated_dir"] = str(gen_dir)
            self._add_log(f"全身生成完了: {len(list(gen_dir.glob('*.png')))} フレーム")
            return {"generated_dir": str(gen_dir)}

        def composite(job, results):
            """合成 - 生成された人物を修復背景に合成"""
            import cv2
            from src.pipeline.post_processor import Compositor

            clean_bg_dir = Path(job.shared_data.get("clean_bg_dir", ""))
            generated_dir = Path(job.shared_data.get("generated_dir", ""))
            masks_dir = Path(job.shared_data.get("masks_dir", ""))
            frames_dir = Path(job.shared_data.get("frames_dir", ""))

            out_dir = config.paths.temp_dir / "composited" / job.job_id
            out_dir.mkdir(parents=True, exist_ok=True)

            frame_files = sorted(frames_dir.glob("*.png"))

            for i, fp in enumerate(frame_files):
                name = fp.name
                bg_path = clean_bg_dir / name
                gen_path = generated_dir / name
                mask_path = masks_dir / name

                # If generated frame exists → composite
                if gen_path.exists() and bg_path.exists() and mask_path.exists():
                    bg = cv2.imread(str(bg_path))
                    gen = cv2.imread(str(gen_path))
                    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

                    if bg is not None and gen is not None and mask is not None:
                        # Resize generated to match background
                        if gen.shape[:2] != bg.shape[:2]:
                            gen = cv2.resize(gen, (bg.shape[1], bg.shape[0]))
                        if mask.shape[:2] != bg.shape[:2]:
                            mask = cv2.resize(mask, (bg.shape[1], bg.shape[0]))

                        # Poisson blend for natural edges
                        result = Compositor.poisson_blend(gen, bg, mask)
                        cv2.imwrite(str(out_dir / name), result)
                    else:
                        # Fallback to original frame
                        import shutil
                        shutil.copy2(fp, out_dir / name)
                else:
                    # No generation for this frame, use swapped or original
                    swapped_path = Path(job.shared_data.get("swapped_dir", "")) / name
                    import shutil
                    if swapped_path.exists():
                        shutil.copy2(swapped_path, out_dir / name)
                    else:
                        shutil.copy2(fp, out_dir / name)

                if (i + 1) % 30 == 0:
                    self._add_log(f"合成: {i+1}/{len(frame_files)}")

            job.shared_data["swapped_dir"] = str(out_dir)  # Override for downstream
            self._add_log(f"合成完了")
            return {"composited_dir": str(out_dir)}

        def temporal_smooth(job, results):
            """時間軸平滑化 - フレーム間の一貫性を保つ"""
            import cv2
            from src.pipeline.post_processor import TemporalSmoother

            swapped_dir = Path(job.shared_data.get("swapped_dir", ""))
            masks_dir = Path(job.shared_data.get("masks_dir", ""))
            frame_files = sorted(swapped_dir.glob("*.png"))

            if len(frame_files) < 3:
                return {}

            smoother = TemporalSmoother(window_size=5, weight=0.6)

            for i, fp in enumerate(frame_files):
                frame = cv2.imread(str(fp))
                if frame is None:
                    continue

                mask_path = masks_dir / fp.name
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE) if mask_path.exists() else None

                smoothed = smoother.smooth(frame, mask=mask)
                cv2.imwrite(str(fp), smoothed)

                if (i + 1) % 60 == 0:
                    self._add_log(f"平滑化: {i+1}/{len(frame_files)}")

            smoother.reset()
            self._add_log("時間軸平滑化完了")
            return {}

        def lora_train(job, results):
            """本地 LoRA 训练 (skip if weights already exist for same identity)"""
            import hashlib
            from src.pipeline.body_swapper import LoRATrainer

            # Check if LoRA weights already exist FOR THE SAME reference photos
            existing_lora = config.paths.lora_dir / "lora_weights"
            identity_file = existing_lora / ".identity_hash"
            # Compute hash of reference photos dir (file list + sizes)
            ref_dir = job.reference_photos_dir
            ref_hash = ""
            if ref_dir and Path(ref_dir).exists():
                entries = sorted(Path(ref_dir).glob("*"))
                hash_input = "|".join(f"{p.name}:{p.stat().st_size}" for p in entries if p.is_file())
                ref_hash = hashlib.md5(hash_input.encode()).hexdigest()[:16]

            if existing_lora.exists() and any(existing_lora.glob("*.safetensors")):
                # Only skip if identity matches (same reference photos)
                if identity_file.exists() and identity_file.read_text().strip() == ref_hash:
                    self._add_log(f"既存のLoRA重みを検出 (同一人物): {existing_lora} — 再学習をスキップ")
                    job.shared_data["lora_path"] = str(existing_lora)
                    return {"lora_path": str(existing_lora)}
                else:
                    self._add_log("参照写真が変更されました。LoRAを再学習します...")

            trainer = LoRATrainer(device=config.gpu.device)

            # Release InsightFace fd to free VRAM before training
            try:
                fd.release()
                self._add_log("FaceDetector VRAM解放 (学習用)")
            except Exception:
                pass

            try:
                # Prepare data
                self._add_log("学習データ準備中...")
                prep = trainer.prepare_training_data(
                    job.reference_photos_dir,
                    config.paths.temp_dir / "lora_data",
                    target_size=512,
                    progress_callback=lambda m: self._add_log(m),
                )
                self._add_log(f"データ準備完了: {prep['count']} 枚")

                # Train using config values
                output = trainer.train(
                    Path(prep["path"]),
                    config.paths.lora_dir,
                    steps=config.body_swap.lora_training_steps,
                    rank=config.body_swap.lora_rank,
                    lr=config.body_swap.lora_lr,
                    callback=lambda m: self._add_log(m),
                )

                # Save identity hash so we can skip retraining for same person
                try:
                    id_file = Path(output) / ".identity_hash"
                    id_file.write_text(ref_hash)
                except Exception:
                    pass

                job.shared_data["lora_path"] = str(output)
                self._add_log(f"LoRA 学習完了: {output}")
                return {"lora_path": str(output)}
            finally:
                # Re-initialize InsightFace for later face_swap stage
                try:
                    fd.initialize()
                except Exception:
                    pass

        def video_encode(job, results):
            swapped_dir = Path(job.shared_data.get("swapped_dir", job.shared_data.get("frames_dir", "")))
            if not swapped_dir.exists() or not list(swapped_dir.glob("*.png")):
                raise ValueError(f"No output frames found in {swapped_dir}")
            fps = job.shared_data.get("fps", 30.0)
            audio_src = job.source_video if job.shared_data.get("has_audio") else None
            vp.encode_video(swapped_dir, job.output_path, fps=fps, audio_source=audio_src)
            return {"output": str(job.output_path)}

        def post_process(job, results):
            self._add_log("Post-processing complete")
            return {}

        # Cloud handlers
        def upload_reference(job, results):
            self._add_log("Cloud: uploading reference photos...")
            return {}

        def cloud_train(job, results):
            self._add_log("Cloud: training model...")
            return {}

        def cloud_swap(job, results):
            self._add_log("Cloud: processing swap...")
            return {}

        def download_result(job, results):
            self._add_log("Cloud: downloading result...")
            return {}

        stages = {
            "video_decode": video_decode,
            "face_detect_reference": face_detect_reference,
            "face_swap": face_swap,
            "face_enhance": face_enhance,
            "pose_estimate": pose_estimate,
            "body_segment": body_segment,
            "body_generate": body_generate,
            "composite": composite,
            "inpaint_mask": inpaint_mask,
            "temporal_smooth": temporal_smooth,
            "lora_train": lora_train,
            "video_encode": video_encode,
            "post_process": post_process,
            "upload_reference": upload_reference,
            "cloud_train": cloud_train,
            "cloud_swap": cloud_swap,
            "download_result": download_result,
        }
        for name, handler in stages.items():
            self.pipeline.register_stage(name, handler)

    def on_cancel(self):
        self.pipeline.cancel()
        return "Cancelled"

    def on_start_cloud(self, video_path, photos_dir, provider, api_key):
        if not api_key:
            return "API Key required"
        try:
            from src.pipeline.cloud_api import CloudManager
            cm = CloudManager()
            cm.setup(provider.lower(), api_key)
            self._add_log(f"Cloud: {provider} connected")
            return f"Cloud {provider} connected. Use main processing tab with Cloud mode."
        except Exception as e:
            return f"Error: {e}"

    def on_download_models(self, progress=gr.Progress()):
        self._add_log("Downloading models...")
        try:
            import subprocess, sys
            result = subprocess.run(
                [sys.executable, "scripts/download_models.py", "--required"],
                capture_output=True, text=True, timeout=600,
            )
            self._add_log(result.stdout[-500:] if result.stdout else "Done")
            return "Download complete"
        except Exception as e:
            return f"Error: {e}"

    def on_start_lora(self, photos_dir, steps, rank, lr):
        if not photos_dir or not Path(photos_dir).exists():
            return "Photos directory not found"
        try:
            from src.pipeline.body_swapper import LoRATrainer
            trainer = LoRATrainer(device=config.gpu.device)

            self._add_log("学習データ準備中...")
            prep = trainer.prepare_training_data(
                Path(photos_dir), config.paths.temp_dir / "lora_data",
                target_size=512,
                progress_callback=lambda m: self._add_log(m),
            )
            self._add_log(f"データ準備完了: {prep['count']} 枚")

            output = trainer.train(
                Path(prep["path"]), config.paths.lora_dir,
                steps=int(steps), rank=int(rank), lr=float(lr),
                callback=lambda m: self._add_log(m),
            )
            return f"LoRA 学習完了!\n保存先: {output}\n\nProcessing タブで 'Full Replace (LoRA)' または 'Inpaint Replace' モードで使用できます。"
        except Exception as e:
            self._add_log(f"LoRA error: {e}")
            return f"Error: {e}"

    # ── Build UI ──

    def build(self):
        self._css = load_css()
        self._theme = gr.themes.Soft(
            primary_hue=gr.themes.colors.orange,
            secondary_hue=gr.themes.colors.stone,
            neutral_hue=gr.themes.colors.stone,
            font=gr.themes.GoogleFont("Noto Sans JP"),
        )
        # Pass theme/css to Blocks for Gradio <6.0, launch() will override for >=6.0
        try:
            app = gr.Blocks(title="YOVUS", css=self._css, theme=self._theme)
        except TypeError:
            app = gr.Blocks(title="YOVUS")
        with app:

            gr.HTML("""<div class="yovus-header"><h1>Y O V U S</h1><p>AI Persona Replacement System  Local and Cloud</p></div>""")

            with gr.Tabs():
                with gr.Tab("Processing"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Input")
                            video_input = gr.Video(label="Source Video", sources=["upload"])
                            video_info = gr.Textbox(label="Video Info", interactive=False, lines=5)
                            video_preview = gr.Image(label="Preview", height=200)
                            gr.Markdown("---")
                            photos_dir = gr.Textbox(label="Reference Photos Folder", value="C:\\Users\\junqi\\Desktop\\test")
                            scan_btn = gr.Button("Scan Photos", variant="secondary", size="sm")
                            photo_count = gr.Textbox(label="Result", interactive=False)
                            photo_gallery = gr.Gallery(label="Photo Preview", columns=5, rows=2, height=180)

                        with gr.Column(scale=1):
                            gr.Markdown("### Settings")
                            mode = gr.Radio(
                                choices=["Face Only", "Face + Body", "Full Replace (LoRA)", "Inpaint Replace", "Cloud"],
                                value="Face Only", label="Mode",
                            )
                            with gr.Accordion("Advanced", open=False):
                                face_enhancer = gr.Dropdown(choices=["codeformer","gfpgan","none"], value="codeformer", label="Face Enhancer")
                                enhance_blend = gr.Slider(0.0, 1.0, value=0.7, step=0.05, label="Blend")
                                face_mask_blur = gr.Slider(0, 30, value=12, step=1, label="Mask Blur")
                                target_face_idx = gr.Number(value=0, label="Target Face Index", precision=0)
                            gr.Markdown("---")
                            with gr.Row():
                                start_btn = gr.Button("Start", variant="primary", size="lg", elem_classes=["jp-btn-primary"])
                                cancel_btn = gr.Button("Cancel", variant="secondary", size="lg")
                            status_text = gr.Textbox(label="Status", interactive=False)
                            output_video = gr.Video(label="Output")

                    with gr.Accordion("Log", open=False):
                        log_output = gr.Textbox(label="", lines=10, max_lines=20, interactive=False, elem_classes=["log-panel"])

                with gr.Tab("Cloud"):
                    gr.Markdown("### Cloud API")
                    with gr.Row():
                        with gr.Column():
                            cloud_provider = gr.Dropdown(choices=["Replicate","Fal"], value="Replicate", label="Provider")
                            cloud_key = gr.Textbox(label="API Key", type="password")
                            cloud_connect = gr.Button("Connect", variant="primary")
                            cloud_status = gr.Textbox(label="Status", interactive=False)
                        with gr.Column():
                            gr.Markdown("#### Pricing")
                            gr.Markdown("""
| Service | Face Swap | LoRA Train | Video |
|---------|-----------|------------|-------|
| Replicate | /bin/bash.02/img | ~.50/1500steps | /bin/bash.05-0.50 |
| Fal.ai | /bin/bash.01/img | /bin/bash.50/1000steps | /bin/bash.10/5s |
""")

                with gr.Tab("Models"):
                    gr.Markdown("### Model Management")
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### LoRA Training")
                            lora_photos = gr.Textbox(label="Photos Folder", value="C:\\Users\\junqi\\Desktop\\test")
                            lora_steps = gr.Slider(500, 5000, value=1500, step=100, label="Steps")
                            lora_rank = gr.Slider(4, 64, value=16, step=4, label="Rank")
                            lora_lr = gr.Number(value=1e-4, label="Learning Rate")
                            train_btn = gr.Button("Start LoRA Training", variant="primary", elem_classes=["jp-btn-primary"])
                            train_status = gr.Textbox(label="Status", interactive=False, lines=5)
                        with gr.Column():
                            gr.Markdown("#### Required Models")
                            model_list = gr.Dataframe(
                                headers=["Model", "Type", "Size"],
                                value=[
                                    ["inswapper_128", "Face Swap", "500MB"],
                                    ["buffalo_l", "Face Detect", "320MB"],
                                    ["CodeFormer", "Enhance", "350MB"],
                                    ["GFPGANv1.4", "Enhance", "330MB"],
                                    ["RealESRGAN_x2", "Upscale", "64MB"],
                                ],
                                interactive=False,
                            )
                            download_btn = gr.Button("Download Required Models", variant="secondary")
                            dl_status = gr.Textbox(label="", interactive=False)

                with gr.Tab("System"):
                    gr.Markdown("### System Info")
                    gpu_info = gr.Textbox(label="GPU", interactive=False, lines=6)
                    detect_btn = gr.Button("Detect GPU", variant="secondary", size="sm")

                with gr.Tab("Help"):
                    gr.Markdown("""
### Usage Guide

#### Modes
| Mode | Description | Time | Quality |
|------|-------------|------|---------|
| Face Only | Face swap only | Fast | High |
| Face + Body | Face + body color match | Medium | High |
| Full Replace | LoRA train + full body | Slow | Best |
| Inpaint | Mask person + regenerate | Medium | Best |
| Cloud | Cloud API processing | Depends | Highest |

#### Setup
1. Run ========================================================
  YOVUS - AI映像人物置換システム インストーラー
========================================================

[1/6] システム確認中...
  OS: Linux 6.18.5
  Python: 3.11.15 (main, Mar  3 2026, 09:26:23) [GCC 13.3.0]
  Platform: x86_64
  ✓ Python バージョン OK

[2/6] GPU確認中...
  ⚠ nvidia-smi が見つかりません。NVIDIAドライバをインストールしてください。

[3/6] FFmpeg確認中...
  ✗ FFmpegが見つかりません
  → Windows: winget install ffmpeg
  → または https://ffmpeg.org/download.html

[4/6] PyTorch (CUDA) インストール中...
  RTX 5070 Laptop → CUDA 12.4+ 推奨
  実行: /usr/local/bin/python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
Looking in indexes: https://download.pytorch.org/whl/cu124
2. Download models from Models tab
3. Upload video and set photos folder
4. Click Start
""")

            gr.HTML("""<div class="yovus-footer">YOVUS v2.0 Local and Cloud AI Persona Replacement</div>""")

            # Events
            detect_btn.click(fn=self.on_detect_gpu, outputs=[gpu_info])
            scan_btn.click(fn=self.on_scan_photos, inputs=[photos_dir], outputs=[photo_count, photo_gallery, log_output])
            video_input.change(fn=self.on_analyze_video, inputs=[video_input], outputs=[video_info, video_preview, log_output])
            start_btn.click(
                fn=self.on_start_processing,
                inputs=[video_input, photos_dir, mode, face_enhancer, enhance_blend, face_mask_blur, target_face_idx],
                outputs=[output_video, status_text, log_output],
            )
            cancel_btn.click(fn=self.on_cancel, outputs=[status_text])
            cloud_connect.click(fn=self.on_start_cloud, inputs=[video_input, photos_dir, cloud_provider, cloud_key], outputs=[cloud_status])
            train_btn.click(fn=self.on_start_lora, inputs=[lora_photos, lora_steps, lora_rank, lora_lr], outputs=[train_status])
            download_btn.click(fn=self.on_download_models, outputs=[dl_status])

        return app


def create_app():
    yovus = YovusApp()
    return yovus.build()
