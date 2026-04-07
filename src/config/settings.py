"""
YOVUS 全局配置
"""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GPUConfig:
    device: str = "cuda"
    vram_limit_gb: float = 7.0
    half_precision: bool = True
    batch_size: int = 1
    onnx_provider: str = "CUDAExecutionProvider"


@dataclass
class VideoConfig:
    max_resolution: tuple = (1920, 1080)
    output_fps: int = 30
    output_codec: str = "libx264"
    output_quality: int = 18
    temp_frame_format: str = "png"
    audio_preserve: bool = True


@dataclass
class FaceSwapConfig:
    detector: str = "retinaface"
    swapper: str = "inswapper_128"
    enhancer: str = "codeformer"
    enhancer_blend: float = 0.7
    face_score_threshold: float = 0.65
    max_faces: int = 5
    face_mask_blur: int = 12
    face_mask_padding: tuple = (0, 0, 0, 0)


@dataclass
class BodySwapConfig:
    pose_estimator: str = "dwpose"
    segmentation_model: str = "u2net"
    controlnet_model: str = "control_v11p_sd15_openpose"
    lora_training_steps: int = 1500
    lora_rank: int = 16
    lora_lr: float = 1e-4
    inference_steps: int = 30
    controlnet_strength: float = 0.85
    guidance_scale: float = 7.5


@dataclass
class PostProcessConfig:
    upscaler: str = "realesrgan_x2"
    denoise_strength: float = 0.4
    color_correction: bool = True
    temporal_smooth: bool = True
    temporal_smooth_weight: float = 0.6
    blend_mode: str = "poisson"


@dataclass
class CloudConfig:
    """云端训练/推理配置"""
    enabled: bool = False
    provider: str = "replicate"  # replicate | fal | runpod
    api_key: str = ""
    # Replicate
    replicate_face_swap_model: str = "yan-ops/face_swap:d5900f9ebed972f9ea8364a4e39b8bfc8e0ef20f1daae4ca7c8a35cf16934fcd"
    replicate_lora_train_model: str = "ostris/flux-dev-lora-trainer"
    replicate_video_inpaint_model: str = "chenxwh/video-repainting"
    # Fal.ai
    fal_face_swap_endpoint: str = "fal-ai/face-swap"
    fal_lora_train_endpoint: str = "fal-ai/flux-lora-fast-training"
    fal_video_gen_endpoint: str = "fal-ai/kling-video/v2/master"
    # RunPod
    runpod_gpu_type: str = "NVIDIA RTX 4090"
    runpod_template_id: str = ""


@dataclass
class InpaintConfig:
    """视频Inpainting涂抹替换配置"""
    enabled: bool = True
    model: str = "propainter"  # propainter | e2fgvi | sd_inpaint
    mask_dilate: int = 15
    mask_blur: int = 9
    flow_completion: bool = True
    temporal_stride: int = 10
    neighbor_length: int = 10


@dataclass
class PathConfig:
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    models_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "models")
    temp_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "temp")
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "output")
    cache_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "cache")
    lora_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "models" / "lora")

    def ensure_dirs(self):
        for d in [self.models_dir, self.temp_dir, self.output_dir, self.cache_dir, self.lora_dir]:
            d.mkdir(parents=True, exist_ok=True)


@dataclass
class AppConfig:
    gpu: GPUConfig = field(default_factory=GPUConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    face_swap: FaceSwapConfig = field(default_factory=FaceSwapConfig)
    body_swap: BodySwapConfig = field(default_factory=BodySwapConfig)
    post_process: PostProcessConfig = field(default_factory=PostProcessConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)
    inpaint: InpaintConfig = field(default_factory=InpaintConfig)
    paths: PathConfig = field(default_factory=PathConfig)

    # UI Settings
    ui_lang: str = "ja"
    ui_theme: str = "japanese"
    server_port: int = 7860
    share: bool = False

    def initialize(self):
        """显式初始化，避免导入时副作用"""
        self.paths.ensure_dirs()


# Global config instance (不自动创建目录，需调用 config.initialize())
config = AppConfig()
