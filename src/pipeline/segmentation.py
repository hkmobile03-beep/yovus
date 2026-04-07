"""
人物分割模块 (修复版)
负责人: 姿态估计专家 (#5) + 图像融合专家 (#7)

Bug修复:
- 修复当所有模型初始化失败时 segment() 崩溃
- 添加初始化状态追踪
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("yovus.segment")


class PersonSegmenter:
    """人物分割 - 从视频帧中提取人物前景"""

    def __init__(self, model_type: str = "u2net", device: str = "cuda"):
        self.model_type = model_type
        self.device = device
        self._model = None
        self._initialized = False
        self._fallback_used = False

    def initialize(self):
        if self._initialized:
            return

        if self.model_type == "u2net":
            self._init_u2net()
        elif self.model_type == "mediapipe":
            self._init_mediapipe()
        else:
            self._init_rembg()

        self._initialized = True

    def _init_u2net(self):
        try:
            from rembg import new_session
            self._model = new_session("u2net_human_seg")
            logger.info("U2Net human segmentation initialized")
        except ImportError:
            logger.warning("rembg not installed, trying MediaPipe")
            self._init_mediapipe()

    def _init_mediapipe(self):
        try:
            import mediapipe as mp
            self._model = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
            self.model_type = "mediapipe"
            logger.info("MediaPipe selfie segmentation initialized")
        except ImportError:
            logger.warning("MediaPipe not available, using OpenCV fallback")
            self.model_type = "opencv"
            self._fallback_used = True

    def _init_rembg(self):
        try:
            from rembg import new_session
            self._model = new_session("u2net")
            self.model_type = "u2net"
            logger.info("rembg (U2Net) initialized")
        except ImportError:
            logger.warning("rembg not available")
            self._init_mediapipe()

    def segment(self, image: np.ndarray) -> np.ndarray:
        """分割人物，返回 mask (0-255)"""
        if not self._initialized:
            self.initialize()

        if self.model_type == "mediapipe" and self._model is not None:
            return self._segment_mediapipe(image)
        elif self.model_type in ("u2net", "rembg") and self._model is not None:
            return self._segment_rembg(image)
        else:
            return self._segment_opencv(image)

    def _segment_mediapipe(self, image: np.ndarray) -> np.ndarray:
        import cv2
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = self._model.process(rgb)
        mask = (result.segmentation_mask * 255).astype(np.uint8)
        mask = cv2.GaussianBlur(mask, (7, 7), 3)
        return mask

    def _segment_rembg(self, image: np.ndarray) -> np.ndarray:
        import cv2
        from rembg import remove

        result = remove(image, session=self._model, only_mask=True)
        if isinstance(result, np.ndarray):
            mask = result
        else:
            mask = np.array(result)

        if len(mask.shape) == 3:
            mask = mask[:, :, 0]

        mask = cv2.GaussianBlur(mask, (5, 5), 2)
        return mask

    def _segment_opencv(self, image: np.ndarray) -> np.ndarray:
        """OpenCV GrabCut 兜底方案"""
        import cv2

        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        rect = (int(w * 0.1), int(h * 0.02), int(w * 0.8), int(h * 0.96))
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        try:
            gc_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.grabCut(image, gc_mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
            mask = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        except cv2.error:
            cv2.ellipse(mask, (w // 2, h // 2), (w // 3, h // 2 - 10), 0, 0, 360, 255, -1)

        mask = cv2.GaussianBlur(mask, (7, 7), 3)
        return mask

    def extract_person(self, image: np.ndarray) -> tuple:
        """提取人物前景，返回: (前景RGBA, mask)"""
        mask = self.segment(image)
        mask_3ch = np.stack([mask] * 3, axis=-1).astype(np.float32) / 255.0

        foreground = (image.astype(np.float32) * mask_3ch).astype(np.uint8)

        rgba = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)
        rgba[:, :, :3] = foreground
        rgba[:, :, 3] = mask

        return rgba, mask

    def release(self):
        if self.model_type == "mediapipe" and self._model is not None:
            try:
                self._model.close()
            except Exception:
                pass
        self._model = None
        self._initialized = False
