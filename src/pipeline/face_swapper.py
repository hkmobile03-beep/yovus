"""
人脸替换引擎
负责人: 人脸替换专家 (#4)
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("yovus.face_swap")


class FaceSwapper:
    """
    人脸替换核心引擎
    集成 inswapper_128 + 增强器
    """

    def __init__(self, device: str = "cuda", half_precision: bool = True):
        self.device = device
        self.half_precision = half_precision
        self._swapper = None
        self._enhancer = None
        self._model_path: Optional[Path] = None

    def initialize(self, models_dir: Path):
        """初始化人脸替换模型"""
        self._model_path = models_dir

        # Initialize inswapper
        try:
            import onnxruntime as ort
            model_file = models_dir / "inswapper_128.onnx"

            if not model_file.exists():
                logger.warning(f"Model not found: {model_file}. Will download on first use.")
                self._download_model(models_dir)
                if not model_file.exists():
                    raise FileNotFoundError(f"Failed to download inswapper model")

            providers = self._get_providers()
            self._swapper = ort.InferenceSession(str(model_file), providers=providers)
            logger.info("inswapper_128 model loaded")

        except ImportError:
            logger.error("onnxruntime not installed")
            raise

    def swap_face(
        self,
        source_face,  # FaceData with embedding
        target_frame: np.ndarray,
        target_face,  # FaceData
    ) -> np.ndarray:
        """
        替换单帧中的人脸
        source_face: 新人物的脸（来自参考照片）
        target_frame: 原始视频帧
        target_face: 原始视频中检测到的脸
        """
        if self._swapper is None:
            raise RuntimeError("Swapper not initialized. Call initialize() first.")

        try:
            import cv2

            # Prepare aligned face for swapper (112x112)
            aligned = self._align_face(target_frame, target_face.landmarks)

            # Run swap model
            blob = cv2.dnn.blobFromImage(
                aligned, 1.0 / 255.0, (128, 128), (0, 0, 0), swapRB=True
            )

            # Use source embedding to guide swap
            source_embedding = source_face.embedding
            if source_embedding is not None:
                source_embedding = source_embedding.reshape(1, -1).astype(np.float32)

            input_name = self._swapper.get_inputs()[0].name
            inputs = {input_name: blob}

            # Add latent/embedding if model supports it
            if len(self._swapper.get_inputs()) > 1:
                latent_name = self._swapper.get_inputs()[1].name
                inputs[latent_name] = source_embedding

            outputs = self._swapper.run(None, inputs)
            swapped = outputs[0]

            # Post-process
            swapped = swapped.squeeze().transpose(1, 2, 0)
            swapped = np.clip(swapped * 255, 0, 255).astype(np.uint8)
            swapped = cv2.cvtColor(swapped, cv2.COLOR_RGB2BGR)
            swapped = cv2.resize(swapped, (128, 128))

            # Paste back
            result = self._paste_face(target_frame, swapped, target_face)
            return result

        except Exception as e:
            logger.error(f"Face swap error: {e}")
            return target_frame  # Return original on error

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

    def _align_face(self, image: np.ndarray, landmarks: Optional[np.ndarray]) -> np.ndarray:
        """对齐人脸到标准位置"""
        import cv2

        if landmarks is None or len(landmarks) < 5:
            return cv2.resize(image, (128, 128))

        # Standard 5-point landmarks for 112x112
        src_pts = np.array([
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041],
        ], dtype=np.float32)

        dst_pts = landmarks[:5].astype(np.float32)

        M = cv2.estimateAffinePartial2D(dst_pts, src_pts)[0]
        if M is None:
            return cv2.resize(image, (112, 112))

        aligned = cv2.warpAffine(image, M, (112, 112))
        return aligned

    def _paste_face(
        self,
        target_frame: np.ndarray,
        swapped_face: np.ndarray,
        target_face,
    ) -> np.ndarray:
        """将替换后的人脸粘贴回原始帧"""
        import cv2

        result = target_frame.copy()
        x1, y1, x2, y2 = target_face.bbox

        # Expand region slightly
        w, h = x2 - x1, y2 - y1
        pad = int(max(w, h) * 0.1)
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(target_frame.shape[1], x2 + pad)
        y2 = min(target_frame.shape[0], y2 + pad)

        # Resize swapped face to target region
        face_resized = cv2.resize(swapped_face, (x2 - x1, y2 - y1))

        # Create seamless blend mask
        mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
        cx, cy = (x2 - x1) // 2, (y2 - y1) // 2
        rx, ry = int((x2 - x1) * 0.4), int((y2 - y1) * 0.45)
        cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
        mask = cv2.GaussianBlur(mask, (15, 15), 8)

        # Blend
        mask_3ch = mask[:, :, np.newaxis].astype(np.float32) / 255.0
        blended = (face_resized * mask_3ch + result[y1:y2, x1:x2] * (1 - mask_3ch)).astype(np.uint8)
        result[y1:y2, x1:x2] = blended

        return result

    def _download_model(self, models_dir: Path):
        """下载 inswapper_128 模型"""
        models_dir.mkdir(parents=True, exist_ok=True)
        logger.info("inswapper_128 model needs to be downloaded manually.")
        logger.info("Please download from: https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx")
        logger.info(f"Place it in: {models_dir / 'inswapper_128.onnx'}")

    def _get_providers(self) -> list:
        if self.device == "cuda":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def release(self):
        self._swapper = None
        self._enhancer = None
