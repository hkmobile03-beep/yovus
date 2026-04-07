"""
人物分割模块 - 前景人物提取
负责人: 姿态估计专家 (#5) + 图像融合专家 (#7)
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("yovus.segment")


class PersonSegmenter:
    """
    人物分割 - 从视频帧中提取人物前景
    支持: SAM2, U2Net, MediaPipe
    """

    def __init__(self, model_type: str = "u2net", device: str = "cuda"):
        self.model_type = model_type
        self.device = device
        self._model = None

    def initialize(self):
        if self.model_type == "u2net":
            self._init_u2net()
        elif self.model_type == "mediapipe":
            self._init_mediapipe()
        else:
            self._init_rembg()

    def _init_u2net(self):
        try:
            from rembg import new_session
            self._model = new_session("u2net_human_seg")
            logger.info("U2Net human segmentation initialized")
        except ImportError:
            logger.warning("rembg not installed, falling back to MediaPipe")
            self._init_mediapipe()

    def _init_mediapipe(self):
        try:
            import mediapipe as mp
            self._model = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
            self.model_type = "mediapipe"
            logger.info("MediaPipe selfie segmentation initialized")
        except ImportError:
            logger.warning("MediaPipe not available")

    def _init_rembg(self):
        try:
            from rembg import new_session
            self._model = new_session("u2net")
            self.model_type = "u2net"
            logger.info("rembg (U2Net) initialized")
        except ImportError:
            logger.error("No segmentation model available")

    def segment(self, image: np.ndarray) -> np.ndarray:
        """
        分割人物，返回 mask (0-255)
        白色=人物, 黑色=背景
        """
        if self._model is None:
            self.initialize()

        if self.model_type == "mediapipe":
            return self._segment_mediapipe(image)
        else:
            return self._segment_rembg(image)

    def _segment_mediapipe(self, image: np.ndarray) -> np.ndarray:
        import cv2
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = self._model.process(rgb)
        mask = (result.segmentation_mask * 255).astype(np.uint8)
        # Smooth mask edges
        mask = cv2.GaussianBlur(mask, (7, 7), 3)
        return mask

    def _segment_rembg(self, image: np.ndarray) -> np.ndarray:
        import cv2
        from rembg import remove

        # rembg returns RGBA image
        result = remove(image, session=self._model, only_mask=True)
        if isinstance(result, np.ndarray):
            mask = result
        else:
            mask = np.array(result)

        if len(mask.shape) == 3:
            mask = mask[:, :, 0]

        mask = cv2.GaussianBlur(mask, (5, 5), 2)
        return mask

    def extract_person(self, image: np.ndarray) -> tuple:
        """
        提取人物前景
        返回: (前景RGBA, mask)
        """
        import cv2

        mask = self.segment(image)
        mask_3ch = np.stack([mask] * 3, axis=-1).astype(np.float32) / 255.0

        foreground = (image.astype(np.float32) * mask_3ch).astype(np.uint8)

        # Create RGBA
        rgba = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)
        rgba[:, :, :3] = foreground
        rgba[:, :, 3] = mask

        return rgba, mask

    def release(self):
        self._model = None
