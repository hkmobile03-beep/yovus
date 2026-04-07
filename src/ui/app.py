"""
YOVUS UI - 日系極簡インターフェース
负责人: UI/UX設計師 (#9)
"""
import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional

import gradio as gr

from src.config.settings import config
from src.core.gpu_manager import GPUManager
from src.core.pipeline_engine import PipelineEngine, PipelineJob

logger = logging.getLogger("yovus.ui")

# ── CSS Theme ──
CSS_PATH = Path(__file__).parent.parent.parent / "assets" / "css" / "japanese_theme.css"


def load_css() -> str:
    if CSS_PATH.exists():
        return CSS_PATH.read_text(encoding="utf-8")
    return ""


class YovusApp:
    """Main Application UI"""

    def __init__(self):
        self.gpu_manager = GPUManager()
        self.pipeline = PipelineEngine()
        self.current_job: Optional[PipelineJob] = None
        self._log_messages: list[str] = []

    def _add_log(self, msg: str, level: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        self._log_messages.append(f"[{timestamp}] {msg}")
        if len(self._log_messages) > 200:
            self._log_messages = self._log_messages[-100:]

    def _get_logs(self) -> str:
        return "\n".join(self._log_messages[-50:])

    # ── Event Handlers ──

    def on_detect_gpu(self) -> str:
        info = self.gpu_manager.detect()
        status = self.gpu_manager.format_status()
        recommendations = self.gpu_manager.get_recommended_settings()
        return f"{status}\n\n推奨設定: {recommendations.get('message', '')}"

    def on_scan_photos(self, photos_dir: str) -> tuple:
        """扫描参考照片目录"""
        if not photos_dir or not Path(photos_dir).exists():
            return "ディレクトリが見つかりません", [], ""

        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = [
            str(f) for f in Path(photos_dir).iterdir()
            if f.suffix.lower() in photo_exts
        ]

        if not photos:
            return "写真が見つかりません", [], ""

        # Show first 20 as preview
        preview = photos[:20]
        info = f"検出: {len(photos)}枚の写真"

        self._add_log(f"参照写真スキャン完了: {len(photos)}枚")
        return info, preview, self._get_logs()

    def on_analyze_video(self, video_path: str) -> tuple:
        """分析视频信息"""
        if not video_path or not Path(video_path).exists():
            return "映像ファイルが見つかりません", None, ""

        try:
            from src.pipeline.video_processor import VideoProcessor
            vp = VideoProcessor(config.paths.temp_dir)
            info = vp.probe(Path(video_path))

            details = (
                f"解像度: {info.width}x{info.height}\n"
                f"FPS: {info.fps:.1f}\n"
                f"フレーム数: {info.frame_count}\n"
                f"長さ: {info.duration:.1f}秒 ({info.duration/60:.1f}分)\n"
                f"コーデック: {info.codec}\n"
                f"音声: {'あり' if info.has_audio else 'なし'}\n"
                f"サイズ: {info.file_size_mb:.1f}MB"
            )

            self._add_log(f"映像分析完了: {info.width}x{info.height}, {info.frame_count}フレーム")

            # Extract a preview frame
            import cv2
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, info.frame_count // 4)
            ret, frame = cap.read()
            cap.release()

            preview = frame if ret else None
            return details, preview, self._get_logs()

        except Exception as e:
            return f"エラー: {e}", None, self._get_logs()

    def on_start_processing(
        self,
        video_path: str,
        photos_dir: str,
        mode: str,
        face_enhancer: str,
        enhance_blend: float,
        face_mask_blur: int,
        target_face_index: int,
        progress=gr.Progress(),
    ) -> tuple:
        """开始处理"""
        if not video_path or not photos_dir:
            return None, "入力が不足しています", self._get_logs()

        mode_map = {
            "顔のみ交換": "face_only",
            "顔＋身体交換": "face_and_body",
            "全身置換（LoRA）": "full_replace",
        }

        job = PipelineJob(
            job_id=f"job_{int(time.time())}",
            source_video=Path(video_path),
            reference_photos_dir=Path(photos_dir),
            output_path=config.paths.output_dir / f"output_{int(time.time())}.mp4",
            mode=mode_map.get(mode, "face_only"),
        )

        self._add_log(f"処理開始: {mode} モード")
        self._add_log(f"入力映像: {video_path}")
        self._add_log(f"参照写真: {photos_dir}")

        # Register stage handlers
        self._register_handlers(face_enhancer, enhance_blend, face_mask_blur, target_face_index)

        # Set progress callback
        def update_progress(prog, stage):
            progress(prog, desc=stage)
            self._add_log(f"進捗: {prog*100:.0f}% - {stage}")

        self.pipeline.set_progress_callback(update_progress)
        self.pipeline.set_log_callback(self._add_log)

        # Run pipeline
        try:
            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(self.pipeline.run(job))
            loop.close()

            if job.status == "completed":
                self._add_log("処理完了!")
                return str(job.output_path), "処理完了", self._get_logs()
            else:
                errors = [r.message for r in results if r.status.value == "failed"]
                return None, f"エラー: {'; '.join(errors)}", self._get_logs()

        except Exception as e:
            self._add_log(f"エラー: {e}")
            return None, f"処理エラー: {e}", self._get_logs()

    def _register_handlers(self, enhancer, blend, blur, face_idx):
        """注册处理阶段"""
        from src.pipeline.video_processor import VideoProcessor
        from src.pipeline.face_detector import FaceDetector
        from src.pipeline.face_swapper import FaceSwapper

        vp = VideoProcessor(config.paths.temp_dir)
        fd = FaceDetector(device=config.gpu.device)
        fs = FaceSwapper(device=config.gpu.device)

        def video_decode(job, results):
            info = vp.probe(job.source_video)
            frames_dir = vp.extract_frames(job.source_video)
            return {"frames_dir": str(frames_dir), "video_info": {"fps": info.fps, "has_audio": info.has_audio}}

        def face_detect_source(job, results):
            # Will detect faces in first frame to identify target
            import cv2
            cap = cv2.VideoCapture(str(job.source_video))
            ret, frame = cap.read()
            cap.release()
            if ret:
                faces = fd.detect(frame)
                return {"face_count": len(faces)}
            return {"face_count": 0}

        def face_detect_reference(job, results):
            refs = fd.extract_best_references(job.reference_photos_dir, max_count=30)
            return {"reference_count": len(refs)}

        def face_swap(job, results):
            self._add_log("顔交換処理中... (フレーム単位)")
            # Process would iterate through frames
            return {"processed_frames": 0}

        def face_enhance(job, results):
            self._add_log("顔補正処理中...")
            return {}

        def video_encode(job, results):
            video_info = {}
            for r in results:
                if "video_info" in r.metadata:
                    video_info = r.metadata["video_info"]
                    break
            self._add_log("映像エンコード中...")
            return {}

        def post_process(job, results):
            self._add_log("後処理中...")
            return {}

        self.pipeline.register_stage("video_decode", video_decode)
        self.pipeline.register_stage("face_detect_source", face_detect_source)
        self.pipeline.register_stage("face_detect_reference", face_detect_reference)
        self.pipeline.register_stage("face_swap", face_swap)
        self.pipeline.register_stage("face_enhance", face_enhance)
        self.pipeline.register_stage("video_encode", video_encode)
        self.pipeline.register_stage("post_process", post_process)

    def on_cancel(self) -> str:
        self.pipeline.cancel()
        self._add_log("処理キャンセル")
        return "キャンセルしました"

    # ── Build UI ──

    def build(self) -> gr.Blocks:
        custom_css = load_css()

        with gr.Blocks(
            title="YOVUS",
            css=custom_css,
            theme=gr.themes.Soft(
                primary_hue=gr.themes.colors.orange,
                secondary_hue=gr.themes.colors.stone,
                neutral_hue=gr.themes.colors.stone,
                font=gr.themes.GoogleFont("Noto Sans JP"),
            ),
        ) as app:
            # ── Header ──
            gr.HTML("""
            <div class="yovus-header">
                <h1>Y O V U S</h1>
                <p>AI映像人物置換システム</p>
            </div>
            """)

            with gr.Tabs():
                # ━━━ Tab 1: メイン処理 ━━━
                with gr.Tab("処理", elem_id="tab-process"):
                    with gr.Row():
                        # Left: Input
                        with gr.Column(scale=1):
                            gr.Markdown("### 入力設定")

                            video_input = gr.Video(
                                label="原始映像",
                                sources=["upload"],
                            )
                            video_info = gr.Textbox(
                                label="映像情報",
                                interactive=False,
                                lines=5,
                            )
                            video_preview = gr.Image(
                                label="プレビュー",
                                visible=True,
                                height=200,
                            )

                            gr.Markdown("---")

                            photos_dir = gr.Textbox(
                                label="参照写真フォルダ",
                                placeholder="C:\\Users\\junqi\\Desktop\\test",
                                value="C:\\Users\\junqi\\Desktop\\test",
                            )
                            scan_btn = gr.Button("写真スキャン", variant="secondary", size="sm")
                            photo_count = gr.Textbox(label="検出結果", interactive=False)
                            photo_gallery = gr.Gallery(
                                label="参照写真プレビュー",
                                columns=5,
                                rows=2,
                                height=180,
                            )

                        # Right: Settings + Output
                        with gr.Column(scale=1):
                            gr.Markdown("### 処理設定")

                            mode = gr.Radio(
                                choices=["顔のみ交換", "顔＋身体交換", "全身置換（LoRA）"],
                                value="顔のみ交換",
                                label="処理モード",
                            )

                            with gr.Accordion("詳細設定", open=False):
                                face_enhancer = gr.Dropdown(
                                    choices=["codeformer", "gfpgan", "gpen", "なし"],
                                    value="codeformer",
                                    label="顔補正モデル",
                                )
                                enhance_blend = gr.Slider(
                                    0.0, 1.0, value=0.7, step=0.05,
                                    label="補正ブレンド率",
                                )
                                face_mask_blur = gr.Slider(
                                    0, 30, value=12, step=1,
                                    label="マスクぼかし",
                                )
                                target_face_idx = gr.Number(
                                    value=0, label="対象人物インデックス",
                                    precision=0,
                                )

                            gr.Markdown("---")

                            with gr.Row():
                                start_btn = gr.Button(
                                    "処理開始",
                                    variant="primary",
                                    size="lg",
                                    elem_classes=["jp-btn-primary"],
                                )
                                cancel_btn = gr.Button(
                                    "キャンセル",
                                    variant="secondary",
                                    size="lg",
                                )

                            status_text = gr.Textbox(
                                label="ステータス",
                                interactive=False,
                            )

                            output_video = gr.Video(
                                label="出力映像",
                            )

                    # Logs
                    with gr.Accordion("処理ログ", open=False):
                        log_output = gr.Textbox(
                            label="",
                            lines=10,
                            max_lines=20,
                            interactive=False,
                            elem_classes=["log-panel"],
                        )

                # ━━━ Tab 2: モデル管理 ━━━
                with gr.Tab("モデル", elem_id="tab-models"):
                    gr.Markdown("### モデル管理")

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### LoRAモデル学習")
                            lora_photos = gr.Textbox(
                                label="学習写真フォルダ",
                                placeholder="C:\\Users\\junqi\\Desktop\\test",
                                value="C:\\Users\\junqi\\Desktop\\test",
                            )
                            with gr.Row():
                                lora_steps = gr.Slider(
                                    500, 5000, value=1500, step=100,
                                    label="学習ステップ数",
                                )
                                lora_rank = gr.Slider(
                                    4, 64, value=16, step=4,
                                    label="LoRAランク",
                                )
                            lora_lr = gr.Number(
                                value=1e-4, label="学習率",
                            )
                            train_btn = gr.Button(
                                "LoRA学習開始",
                                variant="primary",
                                elem_classes=["jp-btn-primary"],
                            )
                            train_status = gr.Textbox(
                                label="学習ステータス",
                                interactive=False,
                                lines=5,
                            )

                        with gr.Column():
                            gr.Markdown("#### インストール済みモデル")
                            model_list = gr.Dataframe(
                                headers=["モデル名", "タイプ", "サイズ", "ステータス"],
                                value=[
                                    ["inswapper_128", "顔交換", "500MB", "未ダウンロード"],
                                    ["codeformer", "顔補正", "350MB", "未ダウンロード"],
                                    ["GFPGANv1.4", "顔補正", "330MB", "未ダウンロード"],
                                    ["RealESRGAN_x2", "超解像", "64MB", "未ダウンロード"],
                                    ["buffalo_l", "顔検出", "320MB", "未ダウンロード"],
                                    ["dwpose", "姿勢推定", "250MB", "未ダウンロード"],
                                    ["u2net_human", "人物分割", "170MB", "未ダウンロード"],
                                    ["SD v1.5", "生成基盤", "4GB", "未ダウンロード"],
                                    ["ControlNet OpenPose", "姿勢制御", "1.4GB", "未ダウンロード"],
                                ],
                                interactive=False,
                            )
                            download_btn = gr.Button(
                                "必須モデル一括ダウンロード",
                                variant="secondary",
                            )

                # ━━━ Tab 3: GPU / System ━━━
                with gr.Tab("システム", elem_id="tab-system"):
                    gr.Markdown("### システム情報")

                    with gr.Row():
                        with gr.Column():
                            gpu_info = gr.Textbox(
                                label="GPU情報",
                                interactive=False,
                                lines=6,
                            )
                            detect_btn = gr.Button(
                                "GPU検出",
                                variant="secondary",
                                size="sm",
                            )

                        with gr.Column():
                            gr.Markdown("#### 推奨設定 (RTX 5070 Laptop 8GB)")
                            gr.Markdown("""
                            | 項目 | 設定値 |
                            |------|--------|
                            | 精度 | FP16 (半精度) |
                            | バッチサイズ | 1 |
                            | 顔補正 | CodeFormer |
                            | 超解像 | Real-ESRGAN x2 |
                            | LoRAランク | 16 |
                            | LoRA学習 | 可能（メモリ節約モード） |
                            """)

                # ━━━ Tab 4: ヘルプ ━━━
                with gr.Tab("ヘルプ", elem_id="tab-help"):
                    gr.Markdown("""
                    ### 使い方ガイド

                    #### Step 1: 準備
                    1. **原始映像**をアップロード（または直接パスを入力）
                    2. **参照写真フォルダ**のパスを入力（1000枚以上推奨）
                    3. 「写真スキャン」で写真を確認

                    #### Step 2: モード選択
                    | モード | 説明 | 処理時間 | 品質 |
                    |--------|------|----------|------|
                    | 顔のみ交換 | 顔だけ交換、身体はそのまま | 速い | 高 |
                    | 顔＋身体交換 | 顔交換＋身体の色調整 | 普通 | 高 |
                    | 全身置換（LoRA） | LoRA学習→全身生成 | 遅い | 最高 |

                    #### Step 3: 処理
                    1. 「処理開始」をクリック
                    2. 処理ログでリアルタイム進捗を確認
                    3. 完了後、出力映像をダウンロード

                    #### 初回セットアップ
                    1. `python scripts/install.py` で依存関係インストール
                    2. 「モデル」タブで必須モデルをダウンロード
                    3. 「システム」タブでGPU検出を確認

                    ---

                    #### トラブルシューティング
                    - **VRAM不足**: モードを「顔のみ交換」に変更
                    - **品質が低い**: 補正ブレンド率を上げる、参照写真を増やす
                    - **処理が遅い**: 映像解像度を下げる、LoRAステップ数を減らす
                    """)

            # ── Footer ──
            gr.HTML("""
            <div class="yovus-footer">
                YOVUS v1.0 — AI映像人物置換システム — Powered by InsightFace · FaceFusion · Stable Diffusion
            </div>
            """)

            # ── Event Bindings ──
            detect_btn.click(fn=self.on_detect_gpu, outputs=[gpu_info])

            scan_btn.click(
                fn=self.on_scan_photos,
                inputs=[photos_dir],
                outputs=[photo_count, photo_gallery, log_output],
            )

            video_input.change(
                fn=self.on_analyze_video,
                inputs=[video_input],
                outputs=[video_info, video_preview, log_output],
            )

            start_btn.click(
                fn=self.on_start_processing,
                inputs=[video_input, photos_dir, mode, face_enhancer, enhance_blend, face_mask_blur, target_face_idx],
                outputs=[output_video, status_text, log_output],
            )

            cancel_btn.click(fn=self.on_cancel, outputs=[status_text])

        return app


def create_app() -> gr.Blocks:
    yovus = YovusApp()
    return yovus.build()
