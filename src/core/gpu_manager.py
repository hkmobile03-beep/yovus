"""
GPU 管理器 - GPU资源监控和优化
负责人: DevOps工程师 (#10)
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("yovus.gpu")


@dataclass
class GPUInfo:
    name: str = "Unknown"
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    temperature: int = 0
    utilization: int = 0
    driver_version: str = ""
    cuda_version: str = ""
    is_available: bool = False


class GPUManager:
    """管理GPU资源分配和监控"""

    def __init__(self):
        self._gpu_info: Optional[GPUInfo] = None

    def detect(self) -> GPUInfo:
        info = GPUInfo()

        # Try PyTorch CUDA
        try:
            import torch
            if torch.cuda.is_available():
                info.is_available = True
                info.name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                info.vram_total_mb = props.total_memory // (1024 * 1024)
                mem_allocated = torch.cuda.memory_allocated(0) // (1024 * 1024)
                mem_reserved = torch.cuda.memory_reserved(0) // (1024 * 1024)
                info.vram_used_mb = mem_reserved
                info.vram_free_mb = info.vram_total_mb - mem_reserved
                info.cuda_version = torch.version.cuda or ""
                logger.info(f"GPU detected via PyTorch: {info.name}")
        except ImportError:
            pass

        # Try pynvml for more details
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info.name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(info.name, bytes):
                info.name = info.name.decode()
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info.vram_total_mb = mem_info.total // (1024 * 1024)
            info.vram_used_mb = mem_info.used // (1024 * 1024)
            info.vram_free_mb = mem_info.free // (1024 * 1024)
            info.temperature = pynvml.nvmlDeviceGetTemperature(handle, 0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            info.utilization = util.gpu
            info.driver_version = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(info.driver_version, bytes):
                info.driver_version = info.driver_version.decode()
            info.is_available = True
            pynvml.nvmlShutdown()
            logger.info(f"GPU detected via NVML: {info.name}")
        except Exception:
            pass

        # Fallback: ONNX Runtime
        if not info.is_available:
            try:
                import onnxruntime
                providers = onnxruntime.get_available_providers()
                if "CUDAExecutionProvider" in providers:
                    info.is_available = True
                    info.name = "CUDA Device (via ONNX Runtime)"
                    logger.info("GPU detected via ONNX Runtime")
            except ImportError:
                pass

        self._gpu_info = info
        return info

    def get_optimal_batch_size(self, model_vram_mb: int = 2000) -> int:
        if not self._gpu_info or not self._gpu_info.is_available:
            return 1
        available = self._gpu_info.vram_free_mb
        # Reserve 1GB for system
        usable = max(0, available - 1024)
        batch = max(1, usable // model_vram_mb)
        return min(batch, 8)  # Cap at 8

    def get_recommended_settings(self) -> dict:
        if not self._gpu_info:
            self.detect()
        info = self._gpu_info

        if not info.is_available:
            return {
                "device": "cpu",
                "half_precision": False,
                "batch_size": 1,
                "face_enhancer": "gfpgan",
                "upscaler": None,
                "lora_possible": False,
                "message": "GPU未検出。CPU処理のみ使用可能です。処理速度は大幅に低下します。"
            }

        vram = info.vram_total_mb

        if vram >= 20000:  # 20GB+
            return {
                "device": "cuda",
                "half_precision": True,
                "batch_size": 4,
                "face_enhancer": "codeformer",
                "upscaler": "realesrgan_x4",
                "lora_possible": True,
                "lora_rank": 64,
                "message": f"ハイエンドGPU: {info.name} ({vram}MB)。全機能利用可能です。"
            }
        elif vram >= 10000:  # 10-20GB
            return {
                "device": "cuda",
                "half_precision": True,
                "batch_size": 2,
                "face_enhancer": "codeformer",
                "upscaler": "realesrgan_x2",
                "lora_possible": True,
                "lora_rank": 32,
                "message": f"高性能GPU: {info.name} ({vram}MB)。全機能利用可能です。"
            }
        elif vram >= 6000:  # 6-10GB (RTX 5070 Laptop = 8GB here)
            return {
                "device": "cuda",
                "half_precision": True,
                "batch_size": 1,
                "face_enhancer": "codeformer",
                "upscaler": "realesrgan_x2",
                "lora_possible": True,
                "lora_rank": 16,
                "message": f"対応GPU: {info.name} ({vram}MB)。メモリ節約モードで全機能利用可能です。"
            }
        else:  # <6GB
            return {
                "device": "cuda",
                "half_precision": True,
                "batch_size": 1,
                "face_enhancer": "gfpgan",
                "upscaler": None,
                "lora_possible": False,
                "message": f"低VRAM GPU: {info.name} ({vram}MB)。顔交換のみ推奨。身体置換にはVRAM不足の可能性。"
            }

    def format_status(self) -> str:
        if not self._gpu_info:
            self.detect()
        info = self._gpu_info
        if not info.is_available:
            return "GPU: 未検出"
        return (
            f"GPU: {info.name}\n"
            f"VRAM: {info.vram_used_mb}MB / {info.vram_total_mb}MB "
            f"(空き {info.vram_free_mb}MB)\n"
            f"温度: {info.temperature}°C | 使用率: {info.utilization}%\n"
            f"Driver: {info.driver_version} | CUDA: {info.cuda_version}"
        )
