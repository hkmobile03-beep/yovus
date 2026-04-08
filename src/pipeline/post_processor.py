"""
后处理模块 - 人脸增强 / 超分辨率 / 帧间一致性 (修复版)
负责人: 后处理专家 (#8)

Bug修复:
- 修复 CodeFormer 初始化不设置 _model 的致命问题
- 修复 GFPGAN/ESRGAN 模型路径使用配置路径
- 修复 ColorCorrector LAB 值范围
- 添加 blend_factor 类型转换保护
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("yovus.post_process")


class FaceEnhancer:
    """人脸质量增强 - CodeFormer / GFPGAN"""

    def __init__(self, model_type: str = "codeformer", device: str = "cuda", models_dir: Optional[Path] = None):
        self.model_type = model_type
        self.device = device
        self.models_dir = models_dir or Path("models")
        self._model = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        if self.model_type == "codeformer":
            self._init_codeformer()
        if self._model is None:
            self._init_gfpgan()
        self._initialized = True

    def _init_codeformer(self):
        try:
            import torch
            from torchvision.transforms.functional import normalize

            # Try loading CodeFormer via basicsr registry
            try:
                from codeformer.basicsr.utils import img2tensor, tensor2img
                from codeformer.basicsr.archs.codeformer_arch import CodeFormer as CodeFormerArch
                from codeformer.facelib.utils.face_restoration_helper import FaceRestoreHelper

                model_path = self.models_dir / "codeformer.pth"
                if not model_path.exists():
                    model_path = self.models_dir / "CodeFormer" / "codeformer.pth"

                if model_path.exists():
                    net = CodeFormerArch(
                        dim_embd=512, codebook_size=1024, n_head=8, n_layers=9,
                        connect_list=['32', '64', '128', '256'],
                    ).to(self.device)
                    ckpt = torch.load(str(model_path), map_location=self.device)
                    net.load_state_dict(ckpt.get("params_ema", ckpt.get("params", ckpt)))
                    net.eval()

                    self._model = {
                        "net": net,
                        "face_helper": FaceRestoreHelper(
                            upscale_factor=1, face_size=512, crop_ratio=(1, 1),
                            det_model='retinaface_resnet50', save_ext='png',
                            device=self.device,
                        ),
                    }
                    self.model_type = "codeformer"
                    logger.info("CodeFormer initialized successfully")
                    return
                else:
                    logger.warning(f"CodeFormer model not found at {model_path}")
            except ImportError:
                pass

            logger.info("CodeFormer package not available, trying GFPGAN")

        except ImportError:
            logger.debug("PyTorch not available for CodeFormer")

    def _init_gfpgan(self):
        try:
            from gfpgan import GFPGANer

            model_path = self.models_dir / "GFPGANv1.4.pth"
            if not model_path.exists():
                logger.warning(f"GFPGAN model not found: {model_path}")
                return

            self._model = GFPGANer(
                model_path=str(model_path),
                upscale=1,
                arch="clean",
                channel_multiplier=2,
                device=self.device,
            )
            self.model_type = "gfpgan"
            logger.info("GFPGAN initialized")
        except ImportError:
            logger.warning("GFPGAN not installed: pip install gfpgan")
        except Exception as e:
            logger.warning(f"GFPGAN init error: {e}")

    def enhance(self, image: np.ndarray, blend_factor: float = 0.7) -> np.ndarray:
        """增强人脸质量"""
        if self._model is None:
            self.initialize()

        if self._model is None:
            return image

        blend_factor = float(max(0.0, min(1.0, blend_factor)))

        try:
            if self.model_type == "gfpgan":
                _, _, output = self._model.enhance(
                    image, has_aligned=False, only_center_face=False, paste_back=True
                )
                if output is not None:
                    output = (output.astype(np.float32) * blend_factor +
                              image.astype(np.float32) * (1 - blend_factor))
                    return np.clip(output, 0, 255).astype(np.uint8)
                return image

            elif self.model_type == "codeformer" and isinstance(self._model, dict):
                return self._enhance_codeformer(image, blend_factor)

            return image

        except Exception as e:
            logger.error(f"Face enhancement error: {e}")
            return image

    def _enhance_codeformer(self, image: np.ndarray, blend_factor: float) -> np.ndarray:
        """CodeFormer enhancement pipeline"""
        try:
            import torch
            import cv2
            from torchvision.transforms.functional import normalize

            net = self._model["net"]
            face_helper = self._model["face_helper"]

            face_helper.clean_all()
            face_helper.read_image(image)
            face_helper.get_face_landmarks_5(only_center_face=False, resize=640, eye_dist_threshold=5)
            face_helper.align_warp_face()

            if not face_helper.cropped_faces:
                return image

            for cropped_face in face_helper.cropped_faces:
                cropped_face_t = torch.from_numpy(
                    cropped_face.transpose(2, 0, 1).astype(np.float32) / 255.0
                ).unsqueeze(0).to(self.device)
                normalize(cropped_face_t, [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], inplace=True)

                with torch.no_grad():
                    output = net(cropped_face_t, w=blend_factor, adain=True)[0]
                    restored_face = output.squeeze().clamp(-1, 1)
                    restored_face = ((restored_face + 1) / 2 * 255).cpu().numpy().transpose(1, 2, 0).astype(np.uint8)
                    # Output is already in BGR order (same as input), no conversion needed

                face_helper.add_restored_face(restored_face)

            face_helper.get_inverse_affine(None)
            result = face_helper.paste_faces_to_input_image()
            return result

        except Exception as e:
            logger.error(f"CodeFormer enhancement error: {e}")
            return image

    def release(self):
        self._model = None
        self._initialized = False


class ImageUpscaler:
    """超分辨率 - Real-ESRGAN"""

    def __init__(self, scale: int = 2, device: str = "cuda", models_dir: Optional[Path] = None):
        self.scale = scale
        self.device = device
        self.models_dir = models_dir or Path("models")
        self._model = None

    def initialize(self):
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet

            model = RRDBNet(
                num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=23, num_grow_ch=32, scale=self.scale,
            )
            model_name = f"RealESRGAN_x{self.scale}plus"
            model_path = self.models_dir / f"{model_name}.pth"

            if not model_path.exists():
                logger.warning(f"Real-ESRGAN model not found: {model_path}")
                return

            self._model = RealESRGANer(
                scale=self.scale,
                model_path=str(model_path),
                model=model,
                half=True,
                device=self.device,
            )
            logger.info(f"Real-ESRGAN x{self.scale} initialized")
        except ImportError:
            logger.warning("Real-ESRGAN not installed: pip install realesrgan")

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
    """帧间一致性平滑 (仅平滑替换区域)"""

    def __init__(self, window_size: int = 5, weight: float = 0.6):
        self.window_size = window_size
        self.weight = weight
        self._buffer: list = []

    def smooth(self, frame: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        """基于时间窗口的帧平滑"""
        self._buffer.append(frame.astype(np.float32))
        if len(self._buffer) > self.window_size:
            self._buffer.pop(0)

        if len(self._buffer) == 1:
            return frame

        weights = np.array([
            self.weight ** (len(self._buffer) - 1 - i)
            for i in range(len(self._buffer))
        ])
        weights /= weights.sum()

        smoothed = np.zeros_like(frame, dtype=np.float32)
        for w, f in zip(weights, self._buffer):
            smoothed += w * f

        smoothed = np.clip(smoothed, 0, 255).astype(np.uint8)

        # 只在 mask 区域应用平滑
        if mask is not None:
            mask_3ch = mask[:, :, np.newaxis].astype(np.float32) / 255.0 if mask.ndim == 2 else mask.astype(np.float32) / 255.0
            result = (smoothed * mask_3ch + frame * (1 - mask_3ch)).astype(np.uint8)
            return result

        return smoothed

    def reset(self):
        self._buffer.clear()


class ColorCorrector:
    """色彩校正 - 匹配原始视频色调"""

    @staticmethod
    def match_color(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """通过LAB色彩空间统计匹配"""
        import cv2

        if source.shape != reference.shape:
            reference = cv2.resize(reference, (source.shape[1], source.shape[0]))

        source_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float64)
        reference_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float64)

        for i in range(3):
            src_mean = source_lab[:, :, i].mean()
            src_std = source_lab[:, :, i].std()
            ref_mean = reference_lab[:, :, i].mean()
            ref_std = reference_lab[:, :, i].std()

            if src_std > 1e-6:
                source_lab[:, :, i] = (source_lab[:, :, i] - src_mean) * (ref_std / src_std) + ref_mean

        source_lab = np.clip(source_lab, 0, 255).astype(np.uint8)
        return cv2.cvtColor(source_lab, cv2.COLOR_LAB2BGR)


class Compositor:
    """图像合成融合"""

    @staticmethod
    def poisson_blend(source: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """泊松融合"""
        import cv2

        if mask.sum() == 0:
            return target

        # 确保 mask 是单通道二值 uint8 (seamlessClone requires 0/255)
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        _, mask = cv2.threshold(mask.astype(np.uint8), 127, 255, cv2.THRESH_BINARY)

        moments = cv2.moments(mask)
        if moments["m00"] == 0:
            return target

        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])

        # 边界安全检查
        h, w = target.shape[:2]
        cx = max(1, min(w - 2, cx))
        cy = max(1, min(h - 2, cy))

        # 确保 source 和 target 尺寸一致
        if source.shape[:2] != target.shape[:2]:
            source = cv2.resize(source, (w, h))
        if mask.shape[:2] != target.shape[:2]:
            mask = cv2.resize(mask, (w, h))

        try:
            result = cv2.seamlessClone(source, target, mask, (cx, cy), cv2.NORMAL_CLONE)
            return result
        except cv2.error as e:
            logger.debug(f"seamlessClone failed: {e}, using alpha blend")
            return Compositor.alpha_blend(source, target, mask)

    @staticmethod
    def alpha_blend(source: np.ndarray, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Alpha 混合"""
        import cv2

        if mask.ndim == 3:
            mask = mask[:, :, 0]

        mask_float = mask.astype(np.float32) / 255.0
        mask_float = cv2.GaussianBlur(mask_float, (21, 21), 11)
        mask_3ch = mask_float[:, :, np.newaxis]

        # 尺寸对齐
        if source.shape[:2] != target.shape[:2]:
            source = cv2.resize(source, (target.shape[1], target.shape[0]))

        result = (source.astype(np.float32) * mask_3ch +
                  target.astype(np.float32) * (1 - mask_3ch))
        return np.clip(result, 0, 255).astype(np.uint8)
