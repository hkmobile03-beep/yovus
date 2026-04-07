"""
YOVUS 全局配置
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GPUConfig:
    device: str = "cuda"
    vram_limit_gb: float = 7.0  # RTX 5070 Laptop safe limit
    half_precision: bool = True  # FP16 to save VRAM
    batch_size: int = 1
    onnx_provider: str = "CUDAExecutionProvider"


@dataclass
class VideoConfig:
    max_resolution: tuple = (1920, 1080)
    output_fps: int = 30
    output_codec: str = "libx264"
    output_quality: int = 18  # CRF value (lower = better)
    temp_frame_format: str = "png"
    audio_preserve: bool = True


@dataclass
class FaceSwapConfig:
    detector: str = "retinaface"  # retinaface | scrfd | yoloface
    swapper: str = "inswapper_128"
    enhancer: str = "codeformer"  # codeformer | gfpgan | gpen
    enhancer_blend: float = 0.7
    face_score_threshold: float = 0.65
    max_faces: int = 5
    face_mask_blur: int = 12
    face_mask_padding: tuple = (0, 0, 0, 0)


@dataclass
class BodySwapConfig:
    pose_estimator: str = "dwpose"  # dwpose | openpose
    segmentation_model: str = "sam2"  # sam2 | u2net
    controlnet_model: str = "control_v11p_sd15_openpose"
    lora_training_steps: int = 1500
    lora_rank: int = 32
    lora_lr: float = 1e-4
    inference_steps: int = 30
    controlnet_strength: float = 0.85
    guidance_scale: float = 7.5


@dataclass
class PostProcessConfig:
    upscaler: str = "realesrgan_x2"  # realesrgan_x2 | realesrgan_x4
    denoise_strength: float = 0.4
    color_correction: bool = True
    temporal_smooth: bool = True
    temporal_smooth_weight: float = 0.6
    blend_mode: str = "poisson"  # poisson | alpha | seamless


@dataclass
class PathConfig:
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    models_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "models")
    temp_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "temp")
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "output")
    cache_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "cache")

    def ensure_dirs(self):
        for d in [self.models_dir, self.temp_dir, self.output_dir, self.cache_dir]:
            d.mkdir(parents=True, exist_ok=True)


@dataclass
class AppConfig:
    gpu: GPUConfig = field(default_factory=GPUConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    face_swap: FaceSwapConfig = field(default_factory=FaceSwapConfig)
    body_swap: BodySwapConfig = field(default_factory=BodySwapConfig)
    post_process: PostProcessConfig = field(default_factory=PostProcessConfig)
    paths: PathConfig = field(default_factory=PathConfig)

    # UI Settings
    ui_lang: str = "ja"  # ja | zh | en
    ui_theme: str = "japanese"
    server_port: int = 7860
    share: bool = False

    def __post_init__(self):
        self.paths.ensure_dirs()


# Global config instance
config = AppConfig()
