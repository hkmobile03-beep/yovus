"""
云端训练/推理 API 集成
负责人: DevOps工程师 (#10) + 生成模型专家 (#6)

支持的云端服务:
- Replicate: 最成熟的AI模型API平台 (face swap / LoRA training / video)
- Fal.ai: 超快推理平台 (face swap / LoRA / Kling video)
- RunPod: GPU云租用 (自定义训练)

推荐最新最强模型:
- Face Swap: Replicate yan-ops/face_swap, Fal fal-ai/face-swap
- LoRA Train: Replicate ostris/flux-dev-lora-trainer, Fal flux-lora-fast-training
- Video: Fal Kling v2, Replicate video-repainting
- Digital Human: LivePortrait, MusePose (开源)
"""
import io
import json
import time
import base64
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("yovus.cloud")


@dataclass
class CloudResult:
    success: bool
    output_url: str = ""
    output_path: Optional[Path] = None
    cost_usd: float = 0.0
    elapsed_seconds: float = 0.0
    message: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ReplicateAPI:
    """
    Replicate.com API 集成
    最强云端 Face Swap + LoRA Training + Video Inpainting
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._client = None

    def initialize(self):
        if not self.api_key:
            raise ValueError("Replicate API Key が必要です。https://replicate.com で取得してください。")
        try:
            import replicate
            self._client = replicate.Client(api_token=self.api_key)
            logger.info("Replicate API initialized")
        except ImportError:
            raise ImportError("replicate パッケージが必要です: pip install replicate")

    def face_swap(
        self,
        source_image_path: Path,
        target_image_path: Path,
        model: str = "yan-ops/face_swap:d5900f9ebed972f9ea8364a4e39b8bfc8e0ef20f1daae4ca7c8a35cf16934fcd",
    ) -> CloudResult:
        """云端人脸替换 (单图)"""
        if self._client is None:
            self.initialize()

        start = time.time()
        try:
            output = self._client.run(
                model,
                input={
                    "source": open(str(source_image_path), "rb"),
                    "target": open(str(target_image_path), "rb"),
                },
            )
            elapsed = time.time() - start

            output_url = str(output) if isinstance(output, str) else str(output[0]) if output else ""

            return CloudResult(
                success=True,
                output_url=output_url,
                elapsed_seconds=elapsed,
                message="顔交換完了 (Replicate)",
                cost_usd=0.02,
            )
        except Exception as e:
            return CloudResult(success=False, message=f"Replicate error: {e}")

    def train_lora(
        self,
        photos_zip_path: Path,
        trigger_word: str = "sks person",
        steps: int = 1500,
        model: str = "ostris/flux-dev-lora-trainer",
        callback: Optional[Callable] = None,
    ) -> CloudResult:
        """
        云端 LoRA 训练 (Flux Dev)
        - 最新最强: Flux Dev LoRA trainer
        - 支持 1000+ 图片训练
        - 高质量人物 LoRA
        """
        if self._client is None:
            self.initialize()

        start = time.time()
        try:
            training = self._client.trainings.create(
                version=model,
                input={
                    "input_images": open(str(photos_zip_path), "rb"),
                    "trigger_word": trigger_word,
                    "steps": steps,
                    "learning_rate": 1e-4,
                    "batch_size": 1,
                    "resolution": "512,768,1024",
                    "autocaption": True,
                },
                destination="yovus/face-model",
            )

            # Poll for completion
            while training.status not in ["succeeded", "failed", "canceled"]:
                time.sleep(10)
                training.reload()
                if callback:
                    callback(f"Training status: {training.status}")

            elapsed = time.time() - start

            if training.status == "succeeded":
                return CloudResult(
                    success=True,
                    output_url=str(training.output),
                    elapsed_seconds=elapsed,
                    message="LoRA学習完了 (Replicate Flux)",
                    cost_usd=steps * 0.001,
                    metadata={"model_url": str(training.output)},
                )
            else:
                return CloudResult(
                    success=False, message=f"Training failed: {training.error}",
                    elapsed_seconds=elapsed,
                )

        except Exception as e:
            return CloudResult(success=False, message=f"Training error: {e}")

    def video_inpaint(
        self,
        video_path: Path,
        mask_video_path: Path,
        model: str = "chenxwh/video-repainting",
    ) -> CloudResult:
        """云端视频修复 (人物区域涂抹替换)"""
        if self._client is None:
            self.initialize()

        start = time.time()
        try:
            output = self._client.run(
                model,
                input={
                    "video": open(str(video_path), "rb"),
                    "mask": open(str(mask_video_path), "rb"),
                },
            )
            elapsed = time.time() - start
            output_url = str(output) if isinstance(output, str) else str(output[0]) if output else ""

            return CloudResult(
                success=True,
                output_url=output_url,
                elapsed_seconds=elapsed,
                message="映像修復完了 (Replicate)",
            )
        except Exception as e:
            return CloudResult(success=False, message=f"Video inpaint error: {e}")


class FalAPI:
    """
    Fal.ai API 集成
    超快推理 + Kling Video + Face Swap
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def initialize(self):
        if not self.api_key:
            raise ValueError("Fal.ai API Key が必要です。https://fal.ai で取得してください。")
        try:
            import fal_client
            logger.info("Fal.ai API initialized")
        except ImportError:
            raise ImportError("fal-client パッケージが必要です: pip install fal-client")

    def face_swap(
        self,
        source_image_path: Path,
        target_image_path: Path,
    ) -> CloudResult:
        """Fal.ai 人脸替换"""
        import fal_client
        import os

        os.environ["FAL_KEY"] = self.api_key
        start = time.time()

        try:
            source_url = fal_client.upload_file(str(source_image_path))
            target_url = fal_client.upload_file(str(target_image_path))

            result = fal_client.subscribe(
                "fal-ai/face-swap",
                arguments={
                    "source_image_url": source_url,
                    "target_image_url": target_url,
                },
            )
            elapsed = time.time() - start

            output_url = result.get("image", {}).get("url", "")
            return CloudResult(
                success=True,
                output_url=output_url,
                elapsed_seconds=elapsed,
                message="顔交換完了 (Fal.ai)",
                cost_usd=0.01,
            )
        except Exception as e:
            return CloudResult(success=False, message=f"Fal.ai error: {e}")

    def train_lora_fast(
        self,
        photos_zip_url: str,
        trigger_word: str = "sks person",
        steps: int = 1000,
        callback: Optional[Callable] = None,
    ) -> CloudResult:
        """
        Fal.ai 超快 LoRA 训练
        Flux LoRA Fast Training - 几分钟内完成
        """
        import fal_client
        import os

        os.environ["FAL_KEY"] = self.api_key
        start = time.time()

        try:
            result = fal_client.subscribe(
                "fal-ai/flux-lora-fast-training",
                arguments={
                    "images_data_url": photos_zip_url,
                    "trigger_word": trigger_word,
                    "steps": steps,
                    "create_masks": True,
                    "is_style": False,
                },
                with_logs=True,
                on_queue_update=lambda update: callback(str(update)) if callback else None,
            )
            elapsed = time.time() - start

            lora_url = result.get("diffusers_lora_file", {}).get("url", "")
            return CloudResult(
                success=True,
                output_url=lora_url,
                elapsed_seconds=elapsed,
                message="LoRA学習完了 (Fal.ai Fast)",
                cost_usd=0.50,
                metadata={"lora_url": lora_url, "config_url": result.get("config_file", {}).get("url", "")},
            )
        except Exception as e:
            return CloudResult(success=False, message=f"Fal.ai training error: {e}")

    def generate_video_kling(
        self,
        image_path: Path,
        prompt: str,
        duration: str = "5",
    ) -> CloudResult:
        """
        Kling v2 Master 视频生成
        最新最强AI视频生成
        """
        import fal_client
        import os

        os.environ["FAL_KEY"] = self.api_key
        start = time.time()

        try:
            image_url = fal_client.upload_file(str(image_path))

            result = fal_client.subscribe(
                "fal-ai/kling-video/v2/master/image-to-video",
                arguments={
                    "prompt": prompt,
                    "image_url": image_url,
                    "duration": duration,
                    "aspect_ratio": "16:9",
                },
            )
            elapsed = time.time() - start

            video_url = result.get("video", {}).get("url", "")
            return CloudResult(
                success=True,
                output_url=video_url,
                elapsed_seconds=elapsed,
                message="映像生成完了 (Kling v2)",
                cost_usd=0.10,
            )
        except Exception as e:
            return CloudResult(success=False, message=f"Kling error: {e}")


class CloudManager:
    """
    云端API统一管理器
    自动选择最优服务提供商
    """

    def __init__(self, config=None):
        self.config = config
        self.replicate: Optional[ReplicateAPI] = None
        self.fal: Optional[FalAPI] = None
        self._available_providers: list[str] = []

    def setup(self, provider: str, api_key: str):
        """设置云端提供商"""
        if provider == "replicate":
            self.replicate = ReplicateAPI(api_key)
            self.replicate.initialize()
            self._available_providers.append("replicate")
        elif provider == "fal":
            self.fal = FalAPI(api_key)
            self.fal.initialize()
            self._available_providers.append("fal")

        logger.info(f"Cloud provider configured: {provider}")

    def is_available(self) -> bool:
        return len(self._available_providers) > 0

    def face_swap(self, source_path: Path, target_path: Path, provider: str = "auto") -> CloudResult:
        """统一人脸替换接口"""
        if provider == "auto":
            if self.fal:
                return self.fal.face_swap(source_path, target_path)
            elif self.replicate:
                return self.replicate.face_swap(source_path, target_path)
        elif provider == "replicate" and self.replicate:
            return self.replicate.face_swap(source_path, target_path)
        elif provider == "fal" and self.fal:
            return self.fal.face_swap(source_path, target_path)

        return CloudResult(success=False, message="クラウドサービスが設定されていません")

    def train_lora(
        self, photos_path: Path, trigger_word: str = "sks person",
        steps: int = 1000, provider: str = "auto", callback: Optional[Callable] = None,
    ) -> CloudResult:
        """统一 LoRA 训练接口"""
        if provider == "auto":
            if self.fal:
                # Fal 需要先上传 zip
                zip_path = self._zip_photos(photos_path)
                import fal_client
                zip_url = fal_client.upload_file(str(zip_path))
                return self.fal.train_lora_fast(zip_url, trigger_word, steps, callback)
            elif self.replicate:
                zip_path = self._zip_photos(photos_path)
                return self.replicate.train_lora(zip_path, trigger_word, steps, callback=callback)

        return CloudResult(success=False, message="クラウドサービスが設定されていません")

    def _zip_photos(self, photos_dir: Path) -> Path:
        """将照片目录打包为 zip"""
        import zipfile
        zip_path = photos_dir.parent / f"{photos_dir.name}_training.zip"

        if zip_path.exists():
            return zip_path

        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in photos_dir.iterdir():
                if f.suffix.lower() in photo_exts:
                    zf.write(f, f.name)

        logger.info(f"Photos zipped: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f}MB)")
        return zip_path

    def get_pricing_info(self) -> dict:
        """获取各服务的定价信息"""
        return {
            "replicate": {
                "face_swap": "$0.02/image",
                "lora_training": "~$1.50/1500steps",
                "video_inpaint": "$0.05-0.50/video",
            },
            "fal": {
                "face_swap": "$0.01/image",
                "lora_training": "$0.50/1000steps (ultra fast)",
                "kling_video": "$0.10/5s video",
            },
        }
