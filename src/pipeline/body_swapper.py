"""
全身替换模块 v3.0 - 本地 LoRA 训练 + ControlNet 生成
RTX 5070 Laptop (8GB VRAM) 完全対応

LoRA 训练流程:
1. 准备训练数据 (裁剪/缩放/自动标注)
2. 缓存 VAE latents (省 VRAM)
3. 训练 UNet LoRA (gradient_checkpointing + fp16 + 8bit Adam)
4. 保存 LoRA 权重

全身生成流程:
1. DWPose 提取骨骼姿势
2. ControlNet (pose) + LoRA → 生成新人物
3. 输出生成图 + mask
"""
import gc
import logging
import json
from pathlib import Path
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger("yovus.body_swap")


class LoRATrainer:
    """LoRA 微调训练器 - 本地 8GB VRAM 优化"""

    def __init__(self, device: str = "cuda", vram_limit_gb: float = 7.0):
        self.device = device
        self.vram_limit_gb = vram_limit_gb

    def prepare_training_data(
        self,
        photos_dir: Path,
        output_dir: Path,
        target_size: int = 512,
        auto_caption: bool = True,
        trigger_word: str = "sks",
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """准备训练数据: 中心裁剪、人脸提取、多样标注"""
        import cv2

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        img_dir = output_dir / "images"
        img_dir.mkdir(exist_ok=True)

        # Clean previous training data to avoid mixing identities
        for old_file in img_dir.glob("*"):
            old_file.unlink(missing_ok=True)

        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = sorted([
            f for f in Path(photos_dir).iterdir()
            if f.suffix.lower() in photo_exts
        ])

        if not photos:
            raise ValueError(f"写真が見つかりません: {photos_dir}")

        # Varied captions for better identity learning
        caption_templates = [
            f"a photo of {trigger_word} person, high quality, detailed face, sharp focus",
            f"a portrait of {trigger_word} person, professional photography, studio lighting",
            f"a photo of {trigger_word} person, natural lighting, high resolution, clear face",
            f"{trigger_word} person, front view, high quality photograph, detailed",
            f"a professional photo of {trigger_word} person, sharp, well-lit, detailed features",
        ]

        # Face close-up caption templates
        face_caption_templates = [
            f"a close up face photo of {trigger_word} person, detailed face, high quality, sharp focus",
            f"a headshot of {trigger_word} person, portrait, studio quality, detailed facial features",
            f"close up portrait of {trigger_word} person, clear face, professional photography",
        ]

        # Initialize face detector for face cropping
        face_cascade = None
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception:
            pass

        processed = 0
        face_crops = 0
        skipped = 0
        total = len(photos)

        for idx, photo in enumerate(photos):
            try:
                img = cv2.imread(str(photo))
                if img is None:
                    skipped += 1
                    continue

                h, w = img.shape[:2]
                if h < 64 or w < 64:
                    skipped += 1
                    continue

                # === Full image: center-crop to square (no gray padding) ===
                crop_size = min(h, w)
                y_start = (h - crop_size) // 2
                x_start = (w - crop_size) // 2
                cropped = img[y_start:y_start + crop_size, x_start:x_start + crop_size]
                resized = cv2.resize(cropped, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

                out_path = img_dir / f"{processed:06d}.png"
                cv2.imwrite(str(out_path), resized)

                if auto_caption:
                    caption = caption_templates[processed % len(caption_templates)]
                    caption_path = img_dir / f"{processed:06d}.txt"
                    caption_path.write_text(caption, encoding="utf-8")

                processed += 1

                # === Face close-up crop (every 3rd image) for identity learning ===
                if face_cascade is not None and idx % 3 == 0:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
                    if len(faces) > 0:
                        # Get largest face
                        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                        # Expand crop area around face (2x padding for context)
                        pad = int(max(fw, fh) * 0.8)
                        fx1 = max(0, fx - pad)
                        fy1 = max(0, fy - pad)
                        fx2 = min(w, fx + fw + pad)
                        fy2 = min(h, fy + fh + pad)
                        face_img = img[fy1:fy2, fx1:fx2]

                        if face_img.size > 0:
                            # Center-crop face region to square
                            fh2, fw2 = face_img.shape[:2]
                            fcs = min(fh2, fw2)
                            fys = (fh2 - fcs) // 2
                            fxs = (fw2 - fcs) // 2
                            face_sq = face_img[fys:fys + fcs, fxs:fxs + fcs]
                            face_resized = cv2.resize(face_sq, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

                            face_path = img_dir / f"{processed:06d}.png"
                            cv2.imwrite(str(face_path), face_resized)

                            if auto_caption:
                                face_caption = face_caption_templates[face_crops % len(face_caption_templates)]
                                face_cap_path = img_dir / f"{processed:06d}.txt"
                                face_cap_path.write_text(face_caption, encoding="utf-8")

                            processed += 1
                            face_crops += 1

                if progress_callback and (idx + 1) % 50 == 0:
                    progress_callback(f"データ準備: {idx + 1}/{total} ({processed} 成功, 顔クロップ {face_crops})")

            except Exception as e:
                logger.debug(f"Skip {photo.name}: {e}")
                skipped += 1

        if progress_callback:
            progress_callback(f"データ準備完了: {processed} 枚 (顔クロップ {face_crops} 枚含む, {skipped} スキップ)")

        logger.info(f"Prepared {processed} training images ({face_crops} face crops) in {img_dir}")
        return {"count": processed, "face_crops": face_crops, "skipped": skipped, "path": str(img_dir)}

    def train(
        self,
        training_data_dir: Path,
        output_dir: Path,
        base_model: str = "runwayml/stable-diffusion-v1-5",
        steps: int = 1500,
        rank: int = 16,
        lr: float = 1e-4,
        trigger_word: str = "sks",
        batch_size: int = 1,
        callback: Optional[Callable] = None,
    ) -> Path:
        """
        本地 LoRA 训练 (8GB VRAM 优化)
        使用 diffusers + PEFT，完整训练循环
        """
        import torch

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        lora_output = output_dir / "lora_weights"
        lora_output.mkdir(exist_ok=True)

        # Save config
        config = {
            "base_model": base_model,
            "steps": steps,
            "rank": rank,
            "lr": lr,
            "trigger_word": trigger_word,
            "training_data": str(training_data_dir),
        }
        (output_dir / "training_config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        if callback:
            callback("LoRA学習開始 (本地GPU)...")
            callback(f"  Base: {base_model}")
            callback(f"  Steps: {steps}, Rank: {rank}, LR: {lr}")

        try:
            return self._train_local(
                training_data_dir, lora_output, base_model,
                steps, rank, lr, trigger_word, batch_size, callback,
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            if callback:
                callback(f"学習エラー: {e}")
            raise

    def _train_local(
        self, data_dir, output_dir, base_model,
        steps, rank, lr, trigger_word, batch_size, callback=None,
    ) -> Path:
        """Real local training loop using diffusers + PEFT"""
        import torch
        from torch.utils.data import Dataset, DataLoader
        from diffusers import AutoencoderKL, UNet2DConditionModel, DDPMScheduler
        from transformers import CLIPTextModel, CLIPTokenizer
        from peft import LoraConfig, get_peft_model
        from PIL import Image
        import cv2

        device = self.device
        dtype = torch.float16

        if callback:
            callback("モデルロード中...")

        # 1) Load tokenizer + text encoder → encode prompt → move to CPU
        tokenizer = CLIPTokenizer.from_pretrained(base_model, subfolder="tokenizer")
        text_encoder = CLIPTextModel.from_pretrained(
            base_model, subfolder="text_encoder", torch_dtype=dtype,
        ).to(device)

        prompt = f"a photo of {trigger_word} person, high quality, detailed"
        tokens = tokenizer(
            prompt, padding="max_length", max_length=tokenizer.model_max_length,
            truncation=True, return_tensors="pt",
        ).input_ids.to(device)

        with torch.no_grad():
            text_embeds = text_encoder(tokens)[0]  # (1, 77, 768)

        # Free text encoder VRAM
        del text_encoder
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback("VAE latents キャッシュ中...")

        # 2) Load VAE → cache latents → free VAE
        vae = AutoencoderKL.from_pretrained(
            base_model, subfolder="vae", torch_dtype=dtype,
        ).to(device)
        vae.eval()

        img_dir = Path(data_dir)
        image_files = sorted(img_dir.glob("*.png"))
        if not image_files:
            raise ValueError(f"No training images found in {img_dir}")

        # Limit to reasonable number for 8GB VRAM training
        max_images = min(len(image_files), 300)
        if len(image_files) > max_images:
            logger.warning(
                f"Training uses {max_images}/{len(image_files)} images "
                f"(VRAM limit). Remaining {len(image_files) - max_images} images skipped."
            )
            if callback:
                callback(f"注意: VRAM制限のため {max_images}/{len(image_files)} 枚のみ使用")
        image_files = image_files[:max_images]

        latent_cache = []
        for i, img_path in enumerate(image_files):
            img = Image.open(img_path).convert("RGB").resize((512, 512))
            img_tensor = torch.from_numpy(
                np.array(img).transpose(2, 0, 1).astype(np.float32) / 127.5 - 1.0
            ).unsqueeze(0).to(device, dtype=dtype)

            with torch.no_grad():
                latent = vae.encode(img_tensor).latent_dist.sample() * vae.config.scaling_factor
                latent_cache.append(latent.cpu())

            if callback and (i + 1) % 50 == 0:
                callback(f"VAEキャッシュ: {i+1}/{len(image_files)}")

        del vae
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback(f"学習データ: {len(latent_cache)} 枚キャッシュ済み")
            callback("UNet + LoRA 準備中...")

        # 3) Load UNet → apply LoRA → prepare training
        unet = UNet2DConditionModel.from_pretrained(
            base_model, subfolder="unet", torch_dtype=dtype,
        ).to(device)

        unet.enable_gradient_checkpointing()

        # Apply LoRA - target cross-attention + self-attention + feedforward for stronger identity
        lora_config = LoraConfig(
            r=rank,
            lora_alpha=rank * 2,  # scaling = 2.0 for stronger identity preservation
            target_modules=[
                "to_k", "to_q", "to_v", "to_out.0",  # cross-attention
                "ff.net.0.proj", "ff.net.2",  # feedforward layers (carry identity info)
                "proj_in", "proj_out",  # projection layers
            ],
            lora_dropout=0.05,
        )
        unet = get_peft_model(unet, lora_config)

        trainable = sum(p.numel() for p in unet.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in unet.parameters())
        if callback:
            callback(f"LoRA パラメータ: {trainable:,} / {total_params:,} ({100*trainable/total_params:.2f}%)")

        # Noise scheduler
        scheduler = DDPMScheduler.from_pretrained(base_model, subfolder="scheduler")

        # Optimizer - ONLY trainable params (saves ~860MB VRAM)
        trainable_params = [p for p in unet.parameters() if p.requires_grad]
        try:
            import bitsandbytes as bnb
            optimizer = bnb.optim.AdamW8bit(
                trainable_params, lr=lr, weight_decay=1e-2,
            )
            if callback:
                callback("オプティマイザ: AdamW 8bit (VRAM節約)")
        except Exception:
            # bitsandbytes can fail with RuntimeError/OSError on Windows (DLL issues)
            optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=1e-2)
            if callback:
                callback("オプティマイザ: AdamW (標準)")

        # Mixed precision scaler for stable fp16 training
        scaler = torch.amp.GradScaler("cuda")

        # Learning rate scheduler - cosine annealing with warmup
        warmup_steps = min(100, steps // 10)
        lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=steps - warmup_steps, eta_min=lr * 0.1,
        )

        # 4) Training loop
        unet.train()
        num_latents = len(latent_cache)
        text_embeds_expanded = text_embeds.to(device, dtype=dtype)

        if callback:
            callback(f"学習開始: {steps} steps (warmup: {warmup_steps})...")

        for step in range(steps):
            # Linear warmup
            if step < warmup_steps:
                warmup_lr = lr * (step + 1) / warmup_steps
                for pg in optimizer.param_groups:
                    pg['lr'] = warmup_lr

            # Random latent from cache (random sampling, not sequential)
            lat_idx = torch.randint(0, num_latents, (1,)).item()
            latent = latent_cache[lat_idx].to(device, dtype=dtype)

            # Random noise
            noise = torch.randn_like(latent)
            timestep = torch.randint(0, scheduler.config.num_train_timesteps, (1,), device=device).long()

            # Add noise
            noisy_latent = scheduler.add_noise(latent, noise, timestep)

            # Forward pass with mixed precision
            with torch.amp.autocast("cuda"):
                noise_pred = unet(
                    noisy_latent, timestep,
                    encoder_hidden_states=text_embeds_expanded,
                ).sample
                loss = torch.nn.functional.mse_loss(noise_pred.float(), noise.float())

            # Backward pass with gradient scaling
            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(unet.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()

            # Step LR scheduler after warmup
            if step >= warmup_steps:
                lr_scheduler.step()

            if callback and (step + 1) % 50 == 0:
                current_lr = optimizer.param_groups[0]['lr']
                callback(f"Step {step+1}/{steps} | Loss: {loss.item():.4f} | LR: {current_lr:.2e}")

            # Save checkpoint
            if (step + 1) % max(1, steps // 3) == 0:
                self._save_lora_diffusers(unet, output_dir / f"checkpoint-{step+1}")

        # 5) Save final weights in diffusers-compatible format
        if callback:
            callback("LoRA 重み保存中...")

        self._save_lora_diffusers(unet, output_dir)

        unet.eval()
        del optimizer, latent_cache, scaler
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback(f"LoRA 学習完了! 保存先: {output_dir}")

        return output_dir

    @staticmethod
    def _save_lora_diffusers(peft_unet, save_dir: Path):
        """Save LoRA weights in PEFT-native format (most compatible with diffusers load_lora_weights)"""
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Remove any old pytorch_lora_weights.safetensors that might conflict
        old_diffusers = save_dir / "pytorch_lora_weights.safetensors"
        if old_diffusers.exists():
            old_diffusers.unlink()

        try:
            # Use PEFT's native save_pretrained - produces adapter_model.safetensors + adapter_config.json
            # This is the most reliable format for diffusers load_lora_weights()
            peft_unet.save_pretrained(str(save_dir))
            logger.info(f"LoRA weights saved (PEFT native format): {save_dir}")
        except Exception as e:
            logger.warning(f"PEFT save_pretrained failed: {e}, trying manual save")
            try:
                from peft import get_peft_model_state_dict
                from safetensors.torch import save_file

                state_dict = get_peft_model_state_dict(peft_unet)
                # Clean up keys for diffusers compatibility
                diffusers_dict = {}
                for key, val in state_dict.items():
                    new_key = key.replace("base_model.model.", "")
                    # Remove adapter name (e.g. ".default") from key path
                    new_key = new_key.replace(".default", "")
                    diffusers_dict[new_key] = val.cpu()

                save_file(diffusers_dict, str(save_dir / "pytorch_lora_weights.safetensors"))
                logger.info(f"LoRA weights saved (manual diffusers format): {save_dir}")
            except Exception as e2:
                logger.error(f"All LoRA save methods failed: {e2}")
                raise


class PoseExtractor:
    """姿態抽出 - DWPose / OpenPose"""

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._detector = None

    def initialize(self):
        try:
            from controlnet_aux import DWposeDetector
            self._detector = DWposeDetector()
            logger.info("DWPose detector initialized")
        except (ImportError, Exception) as e:
            logger.warning(f"DWPose not available: {e}, trying OpenPose")
            try:
                from controlnet_aux import OpenposeDetector
                self._detector = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
                logger.info("OpenPose detector initialized")
            except (ImportError, Exception) as e2:
                logger.warning(f"OpenPose not available: {e2}")
                self._detector = None

    def extract_pose(self, image: np.ndarray) -> Optional[np.ndarray]:
        """从图像中提取姿势骨骼图"""
        if self._detector is None:
            self.initialize()
        if self._detector is None:
            return self._fallback_pose(image)

        from PIL import Image
        import cv2

        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        pose_img = self._detector(pil_img)

        pose_np = np.array(pose_img)
        pose_np = cv2.cvtColor(pose_np, cv2.COLOR_RGB2BGR)

        # Resize to match input
        if pose_np.shape[:2] != image.shape[:2]:
            pose_np = cv2.resize(pose_np, (image.shape[1], image.shape[0]))

        return pose_np

    def _fallback_pose(self, image: np.ndarray) -> np.ndarray:
        """无姿势检测时使用OpenCV DNN人体姿势估计"""
        import cv2

        h, w = image.shape[:2]
        # Create black canvas for pose drawing (like OpenPose output)
        canvas = np.zeros((h, w, 3), dtype=np.uint8)

        # Use OpenCV's built-in person detector to find the person region
        # Then draw a simple stick figure based on body proportions
        # This is much better than Canny edges for ControlNet
        try:
            # Try OpenCV DNN pose estimation
            proto = cv2.data.haarcascades + "haarcascade_fullbody.xml"
            body_cascade = cv2.CascadeClassifier(proto)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bodies = body_cascade.detectMultiScale(gray, 1.1, 3)

            if len(bodies) > 0:
                # Draw person silhouette on black background
                bx, by, bw, bh = max(bodies, key=lambda b: b[2]*b[3])

                # Draw simplified stick figure
                cx = bx + bw // 2  # center x
                head_y = by + bh // 8
                neck_y = by + bh // 5
                hip_y = by + int(bh * 0.55)
                knee_y = by + int(bh * 0.78)
                foot_y = by + bh
                shoulder_w = bw // 3

                color = (255, 255, 255)
                thickness = max(2, min(w, h) // 150)

                # Head circle
                cv2.circle(canvas, (cx, head_y), bh // 10, color, thickness)
                # Spine
                cv2.line(canvas, (cx, neck_y), (cx, hip_y), color, thickness)
                # Shoulders
                cv2.line(canvas, (cx - shoulder_w, neck_y + 10), (cx + shoulder_w, neck_y + 10), color, thickness)
                # Arms
                cv2.line(canvas, (cx - shoulder_w, neck_y + 10), (cx - shoulder_w - bw//6, hip_y), color, thickness)
                cv2.line(canvas, (cx + shoulder_w, neck_y + 10), (cx + shoulder_w + bw//6, hip_y), color, thickness)
                # Legs
                cv2.line(canvas, (cx, hip_y), (cx - bw//4, knee_y), color, thickness)
                cv2.line(canvas, (cx, hip_y), (cx + bw//4, knee_y), color, thickness)
                cv2.line(canvas, (cx - bw//4, knee_y), (cx - bw//5, foot_y), color, thickness)
                cv2.line(canvas, (cx + bw//4, knee_y), (cx + bw//5, foot_y), color, thickness)

                return canvas
        except Exception:
            pass

        # Last resort: return black image with white center silhouette
        # ControlNet will generate a centered standing person
        cx, cy = w // 2, h // 2
        cv2.ellipse(canvas, (cx, cy - h//6), (w//8, h//4), 0, 0, 360, (255, 255, 255), 2)
        cv2.line(canvas, (cx, cy), (cx, cy + h//4), (255, 255, 255), 2)
        return canvas

    def release(self):
        self._detector = None
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass


class BodyGenerator:
    """全身生成 - ControlNet (Pose) + LoRA"""

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._pipe = None
        self._initialized = False

    def initialize(self, lora_path: Optional[Path] = None, base_model: str = "runwayml/stable-diffusion-v1-5"):
        """初始化 ControlNet + SD + LoRA Pipeline"""
        if self._initialized:
            return

        import torch
        from diffusers import (
            StableDiffusionControlNetPipeline,
            ControlNetModel,
            UniPCMultistepScheduler,
        )

        logger.info("Loading ControlNet (openpose)...")
        try:
            controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/control_v11p_sd15_openpose",
                torch_dtype=torch.float16,
            )
        except Exception as e:
            logger.error(f"ControlNet download/load failed: {e}")
            raise RuntimeError(
                "ControlNet モデルのダウンロードに失敗しました。"
                "ネットワーク接続を確認するか、手動でモデルをダウンロードしてください: "
                "lllyasviel/control_v11p_sd15_openpose"
            ) from e

        logger.info("Loading Stable Diffusion pipeline...")
        try:
            self._pipe = StableDiffusionControlNetPipeline.from_pretrained(
                base_model,
                controlnet=controlnet,
                torch_dtype=torch.float16,
                safety_checker=None,
            )
        except Exception as e:
            logger.error(f"SD pipeline load failed: {e}")
            raise RuntimeError(
                f"Stable Diffusion パイプラインのロードに失敗: {e}"
            ) from e

        self._pipe.scheduler = UniPCMultistepScheduler.from_config(
            self._pipe.scheduler.config
        )

        # Load LoRA BEFORE cpu_offload (offload hooks can interfere with weight injection)
        if lora_path and Path(lora_path).exists():
            lora_path = Path(lora_path)
            logger.info(f"Loading LoRA weights from: {lora_path}")
            try:
                self._pipe.load_lora_weights(str(lora_path))
                logger.info("LoRA weights loaded successfully")
            except Exception as lora_err:
                logger.warning(f"Standard LoRA load failed: {lora_err}")
                # Try loading individual safetensors file directly
                safetensors_files = list(lora_path.glob("*.safetensors"))
                if safetensors_files:
                    try:
                        self._pipe.load_lora_weights(str(safetensors_files[0]))
                        logger.info(f"LoRA loaded from file: {safetensors_files[0].name}")
                    except Exception as e2:
                        logger.error(f"All LoRA load attempts failed: {e2}")
                else:
                    logger.error("No safetensors files found in LoRA directory")

        # 8GB VRAM optimization (must be after LoRA loading)
        self._pipe.enable_model_cpu_offload()
        try:
            self._pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            logger.debug("xformers not available")

        self._initialized = True
        logger.info("Body generation pipeline ready")

    def generate(
        self,
        pose_image: np.ndarray,
        prompt: str = "a photo of sks person, full body, high quality, detailed, professional photography",
        negative_prompt: str = "low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly",
        num_inference_steps: int = 30,
        controlnet_conditioning_scale: float = 0.85,
        guidance_scale: float = 7.5,
        width: int = 512,
        height: int = 768,
        seed: int = -1,
    ) -> np.ndarray:
        """根据姿态图生成全身人物"""
        if self._pipe is None:
            raise RuntimeError("Pipeline not initialized")

        import torch
        from PIL import Image
        import cv2

        # Ensure dimensions are divisible by 8 (required by VAE)
        width = (width // 8) * 8
        height = (height // 8) * 8

        # Convert pose to PIL
        pose_pil = Image.fromarray(cv2.cvtColor(pose_image, cv2.COLOR_BGR2RGB))
        pose_pil = pose_pil.resize((width, height))

        generator = None
        if seed >= 0:
            generator = torch.Generator(device="cpu").manual_seed(seed)

        result = self._pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=pose_pil,
            num_inference_steps=num_inference_steps,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]

        result_np = np.array(result)
        result_np = cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)
        return result_np

    def release(self):
        self._pipe = None
        self._initialized = False
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass
