"""
后处理模块 - 人脸增强 / 超分辨率 / 帧间一致性
负责人: 后处理专家 (#8)
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("yovus.post_process")


class FaceEnhancer:
    """人脸质量增强 - CodeFormer / GFPGAN"""

    def __init__(self, model_type: str = "codeformer", device: str = "cuda"):
        self.model_type = model_type
        self.device = device
        self._model = None

    def initialize(self):
        if self.model_type == "codeformer":
            self._init_codeformer()
        else:
            self._init_gfpgan()

    def _init_codeformer(self):
        try:
            from codeformer.facelib.utils.face_restoration_helper import FaceRestoreHelper
            logger.info("CodeFormer initialized")
        except ImportError:
            logger.warning("CodeFormer not installed. Falling back to GFPGAN.")
            self._init_gfpgan()

    def _init_gfpgan(self):
        try:
            from gfpgan import GFPGANer
            self._model = GFPGANer(
                model_path="models/GFPGANv1.4.pth",
                upscale=1,
                arch="clean",
                channel_multiplier=2,
            )
            self.model_type = "gfpgan"
            logger.info("GFPGAN initialized")
        except ImportError:
            logger.warning("GFPGAN not installed")

    def enhance(self, image: np.ndarray, blend_factor: float = 0.7) -> np.ndarray:
        """增强人脸质量"""
        if self._model is None:
            self.initialize()

        if self._model is None:
            return image

        try:
            if self.model_type == "gfpgan":
                _, _, output = self._model.enhance(
                    image, has_aligned=False, only_center_face=False, paste_back=True
                )
                # Blend with original
                output = (output * blend_factor + image * (1 - blend_factor)).astype(np.uint8)
                return output
            else:
                return image
        except Exception as e:
            logger.error(f"Face enhancement error: {e}")
            return image

    def release(self):
        self._model = None


class ImageUpscaler:
    """超分辨率 - Real-ESRGAN"""

    def __init__(self, scale: int = 2, device: str = "cuda"):
        self.scale = scale
        self.device = device
        self._model = None

    def initialize(self):
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet

            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=self.scale)
            model_name = f"RealESRGAN_x{self.scale}plus"

            self._model = RealESRGANer(
                scale=self.scale,
                model_path=f"models/{model_name}.pth",
                model=model,
                half=True,
                device=self.device,
            )
            logger.info(f"Real-ESRGAN x{self.scale} initialized")
        except ImportError:
            logger.warning("Real-ESRGAN not installed")

    def upscale(self, image: np.ndarray) -> np.ndarray:
        if self._model is None:
            self.initialize()
        if self._model is None:
            return image

        try:
            output, _ = self._model.enhance(image, outscale=self.scale)
            return output
        except Exception as e:
            logger.error(f"Upscale error: {e}")
            return image

    def release(self):
        self._model = None


class TemporalSmoother:
    """帧间一致性平滑"""

    def __init__(self, window_size: int = 5, weight: float = 0.6):
        self.window_size = window_size
        self.weight = weight
        self._buffer: list = []

    def smooth(self, frame: np.ndarray) -> np.ndarray:
        """基于时间窗口的帧平滑"""
        self._buffer.append(frame.astype(np.float32))
        if len(self._buffer) > self.window_size:
            self._buffer.pop(0)

        if len(self._buffer) == 1:
            return frame

        # Weighted average: recent frames have higher weight
        weights = np.array([
            self.weight ** (len(self._buffer) - 1 - i)
            for i in range(len(self._buffer))
        ])
        weights /= weights.sum()

        result = np.zeros_like(frame, dtype=np.float32)
        for w, f in zip(weights, self._buffer):
            result += w * f

        return np.clip(result, 0, 255).astype(np.uint8)

    def reset(self):
        self._buffer.clear()


class ColorCorrector:
    """色彩校正 - 匹配原始视频色调"""

    @staticmethod
    def match_color(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """通过直方图匹配校正颜色"""
        import cv2

        # Convert to LAB color space
        source_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
        reference_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float32)

        # Match statistics for each channel
        for i in range(3):
            src_mean, src_std = source_lab[:, :, i].mean(), source_lab[:, :, i].std()
            ref_mean, ref_std = reference_lab[:, :, i].mean(), reference_lab[:, :, i].std()

            if src_std > 0:
                source_lab[:, :, i] = (source_lab[:, :, i] - src_mean) * (ref_std / src_std) + ref_mean

        source_lab = np.clip(source_lab, 0, 255).astype(np.uint8)
        return cv2.cvtColor(source_lab, cv2.COLOR_LAB2BGR)


class Compositor:
    """图像合成融合"""

    @staticmethod
    def poisson_blend(source: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """泊松融合 - 无缝粘贴"""
        import cv2

        # Find center of mask
        moments = cv2.moments(mask)
        if moments["m00"] == 0:
            return target

        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
        center = (cx, cy)

        try:
            result = cv2.seamlessClone(source, target, mask, center, cv2.NORMAL_CLONE)
            return result
        except Exception:
            # Fallback to alpha blending
            return Compositor.alpha_blend(source, target, mask)

    @staticmethod
    def alpha_blend(source: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Alpha 混合"""
        import cv2

        mask_float = mask.astype(np.float32) / 255.0
        if len(mask_float.shape) == 2:
            mask_float = mask_float[:, :, np.newaxis]

        # Feather edges
        mask_float = cv2.GaussianBlur(mask_float, (21, 21), 11)
        if len(mask_float.shape) == 2:
            mask_float = mask_float[:, :, np.newaxis]

        result = (source * mask_float + target * (1 - mask_float)).astype(np.uint8)
        return result
