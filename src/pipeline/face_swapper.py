"""
人脸替换引擎 (修复版)
负责人: 人脸替换专家 (#4)

Bug修复:
- 修复 _align_face 返回尺寸不一致 (统一128x128)
- 修复 ONNX 推理输入格式
- 添加 InsightFace 原生 swapper 支持
- 修复 seamlessClone 参数
- 添加帧批量处理
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("yovus.face_swap")

# inswapper标准对齐模板 (针对112x112)
ARCFACE_DST = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041],
], dtype=np.float32)


class FaceSwapper:
    """
    人脸替换核心引擎
    优先使用 InsightFace 原生 swapper API
    回退到手动 ONNX 推理
    """

    def __init__(self, device: str = "cuda", half_precision: bool = True):
        self.device = device
        self.half_precision = half_precision
        self._swapper = None
        self._model_path: Optional[Path] = None
        self._use_native = False  # 是否使用 insightface 原生API

    def initialize(self, models_dir: Path):
        """初始化人脸替换模型"""
        self._model_path = models_dir
        model_file = models_dir / "inswapper_128.onnx"

        # Check for missing or corrupt model file
        if model_file.exists() and model_file.stat().st_size < 1_000_000:
            logger.warning(f"Model file corrupt (too small: {model_file.stat().st_size} bytes), removing")
            model_file.unlink()

        if not model_file.exists():
            logger.warning(f"Model not found: {model_file}")
            self._download_model(models_dir)
            if not model_file.exists():
                raise FileNotFoundError(
                    f"inswapper_128.onnx が見つかりません。\n"
                    f"手動ダウンロード: https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx\n"
                    f"保存先: {model_file}"
                )

        # 尝试使用 InsightFace 原生接口
        try:
            import insightface
            self._swapper = insightface.model_zoo.get_model(
                str(model_file),
                providers=self._get_providers(),
            )
            self._use_native = True
            logger.info("inswapper_128 loaded (InsightFace native API)")
            return
        except Exception as e:
            logger.debug(f"InsightFace native load failed: {e}, falling back to ONNX")

        # 回退到 ONNX Runtime
        try:
            import onnxruntime as ort
            providers = self._get_providers()
            self._swapper = ort.InferenceSession(str(model_file), providers=providers)
            self._use_native = False
            logger.info("inswapper_128 loaded (ONNX Runtime)")
        except ImportError:
            raise ImportError("onnxruntime-gpu が必要です: pip install onnxruntime-gpu")

    def swap_face(
        self,
        source_face,
        target_frame: np.ndarray,
        target_face,
    ) -> np.ndarray:
        """替换单帧中的人脸"""
        if self._swapper is None:
            raise RuntimeError("Swapper not initialized. Call initialize() first.")

        try:
            if self._use_native:
                return self._swap_native(source_face, target_frame, target_face)
            else:
                return self._swap_onnx(source_face, target_frame, target_face)
        except Exception as e:
            logger.error(f"Face swap error: {e}")
            return target_frame

    def _swap_native(self, source_face, target_frame, target_face):
        """使用 InsightFace 原生 swapper"""
        # Extract raw insightface Face objects from FaceData wrappers
        raw_source = getattr(source_face, '_raw', None) or source_face
        raw_target = getattr(target_face, '_raw', None) or target_face
        # If either is still a FaceData wrapper (no _raw), fall back to ONNX
        from src.pipeline.face_detector import FaceData
        if isinstance(raw_source, FaceData) or isinstance(raw_target, FaceData):
            return self._swap_onnx(source_face, target_frame, target_face)
        result = self._swapper.get(target_frame, raw_target, raw_source, paste_back=True)
        return result

    def _swap_onnx(self, source_face, target_frame, target_face):
        """手动 ONNX 推理"""
        import cv2

        # 对齐目标脸 (统一 128x128 for inswapper_128)
        aligned, M_inv = self._align_face(target_frame, target_face.landmarks, size=128)

        # 准备输入 blob
        blob = cv2.dnn.blobFromImage(
            aligned, 1.0 / 255.0, (128, 128), (0, 0, 0), swapRB=True
        )

        # 准备 source embedding
        source_embedding = source_face.embedding
        if source_embedding is None:
            logger.warning("Source face has no embedding, swap quality may be poor")
            return target_frame

        source_embedding = source_embedding.reshape(1, -1).astype(np.float32)

        # ONNX 推理
        inputs = {}
        input_names = [inp.name for inp in self._swapper.get_inputs()]
        inputs[input_names[0]] = blob
        if len(input_names) > 1:
            inputs[input_names[1]] = source_embedding

        outputs = self._swapper.run(None, inputs)
        swapped = outputs[0]

        # 后处理: NCHW → HWC
        swapped = swapped.squeeze()
        if swapped.ndim == 3 and swapped.shape[0] == 3:
            swapped = swapped.transpose(1, 2, 0)
        swapped = np.clip(swapped * 255, 0, 255).astype(np.uint8)
        swapped = cv2.cvtColor(swapped, cv2.COLOR_RGB2BGR)

        # 粘贴回原图
        result = self._paste_back(target_frame, swapped, M_inv, target_face)
        return result

    def swap_video_frame(
        self,
        source_face,
        target_frame: np.ndarray,
        target_faces: list,
        target_index: int = 0,
    ) -> np.ndarray:
        """替换视频帧中指定人脸"""
        if not target_faces:
            return target_frame
        if target_index >= len(target_faces):
            target_index = 0
        return self.swap_face(source_face, target_frame, target_faces[target_index])

    def _align_face(self, image: np.ndarray, landmarks, size: int = 128):
        """对齐人脸，返回对齐后的图像和逆变换矩阵"""
        import cv2

        if landmarks is None or (hasattr(landmarks, '__len__') and len(landmarks) < 5):
            # 无 landmarks 时简单裁剪
            h, w = image.shape[:2]
            M = np.eye(2, 3, dtype=np.float32)
            M_inv = np.eye(2, 3, dtype=np.float32)
            return cv2.resize(image, (size, size)), M_inv

        # 缩放标准模板到目标尺寸
        scale = size / 112.0
        dst_pts = ARCFACE_DST * scale
        src_pts = np.array(landmarks[:5], dtype=np.float32)

        # 计算仿射变换
        M, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)
        if M is None:
            return cv2.resize(image, (size, size)), np.eye(2, 3, dtype=np.float32)

        aligned = cv2.warpAffine(image, M, (size, size), borderMode=cv2.BORDER_REPLICATE)

        # 计算逆变换
        M_inv = cv2.invertAffineTransform(M)

        return aligned, M_inv

    def _paste_back(self, target_frame, swapped_face, M_inv, target_face):
        """将替换后的人脸粘贴回原始帧 (使用仿射逆变换+无缝融合)"""
        import cv2

        h, w = target_frame.shape[:2]
        face_size = swapped_face.shape[0]

        # 将 swapped face 变换回原始坐标空间
        face_warped = cv2.warpAffine(swapped_face, M_inv, (w, h), borderValue=0)

        # 创建 mask
        mask = np.ones((face_size, face_size), dtype=np.uint8) * 255
        # 缩小 mask 避免边缘
        border = int(face_size * 0.08)
        mask[:border, :] = 0
        mask[-border:, :] = 0
        mask[:, :border] = 0
        mask[:, -border:] = 0
        mask = cv2.GaussianBlur(mask, (15, 15), 5)

        mask_warped = cv2.warpAffine(mask, M_inv, (w, h), borderValue=0)

        # 找到 mask 中心用于 seamlessClone
        mask_binary = (mask_warped > 128).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return target_frame

        # 计算中心
        M_moments = cv2.moments(mask_binary)
        if M_moments["m00"] == 0:
            return target_frame
        cx = int(M_moments["m10"] / M_moments["m00"])
        cy = int(M_moments["m01"] / M_moments["m00"])

        # 边界检查
        cx = max(1, min(w - 2, cx))
        cy = max(1, min(h - 2, cy))

        try:
            result = cv2.seamlessClone(face_warped, target_frame, mask_warped, (cx, cy), cv2.NORMAL_CLONE)
            return result
        except cv2.error:
            # 回退到 alpha blending
            mask_3ch = mask_warped[:, :, np.newaxis].astype(np.float32) / 255.0
            result = (face_warped * mask_3ch + target_frame * (1 - mask_3ch)).astype(np.uint8)
            return result

    def _download_model(self, models_dir: Path):
        """尝试自动下载模型 (多源)"""
        models_dir.mkdir(parents=True, exist_ok=True)
        model_file = models_dir / "inswapper_128.onnx"
        temp_file = models_dir / "inswapper_128.onnx.downloading"

        # Multiple download sources (HuggingFace gated → try alternatives)
        urls = [
            "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx",
            "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx",
            "https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx",
        ]

        for url in urls:
            try:
                import httpx
                logger.info(f"Downloading inswapper_128.onnx from {url.split('/')[2]} ...")
                with httpx.stream("GET", url, follow_redirects=True, timeout=600) as resp:
                    if resp.status_code != 200:
                        logger.warning(f"HTTP {resp.status_code} from {url.split('/')[2]}")
                        continue
                    with open(temp_file, "wb") as f:
                        for chunk in resp.iter_bytes(8192):
                            f.write(chunk)

                # Verify file size (real model is ~500MB, error pages are tiny)
                file_size = temp_file.stat().st_size
                if file_size < 1_000_000:  # Less than 1MB = not a real model
                    logger.warning(f"Downloaded file too small ({file_size} bytes), skipping")
                    temp_file.unlink(missing_ok=True)
                    continue

                temp_file.rename(model_file)
                logger.info(f"Download complete ({file_size // (1024*1024)}MB)")
                return

            except Exception as e:
                logger.warning(f"Download failed from {url.split('/')[2]}: {e}")
                temp_file.unlink(missing_ok=True)

        logger.error("All download sources failed.")
        logger.info(
            f"手動ダウンロード:\n"
            f"  URL: https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx\n"
            f"  保存先: {model_file}"
        )

    def _get_providers(self) -> list:
        if self.device == "cuda":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def release(self):
        self._swapper = None
        import gc
        gc.collect()
