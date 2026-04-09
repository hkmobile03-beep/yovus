"""Face detection + embedding via InsightFace (buffalo_l).

Only used locally for identifying who is in the target video and for choosing
the best source photo. The actual face swap is delegated to fal.ai.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np


@dataclass
class DetectedFace:
    """A single face detected in an image or video frame."""

    frame_index: int            # Frame number inside the source video (-1 for still images)
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2 in pixels
    det_score: float            # Detector confidence, 0..1
    embedding: np.ndarray       # 512-d L2-normalized face embedding
    image: np.ndarray           # Cropped face thumbnail (BGR)

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)


class FaceDetector:
    """Thin wrapper over ``insightface.app.FaceAnalysis``.

    Provides face detection, embeddings, and thumbnail crops. No swap model
    is loaded — the inswapper weights are *not* required.
    """

    def __init__(
        self,
        det_size: int = 640,
        providers: Optional[Sequence[str]] = None,
        model_name: str = "buffalo_l",
    ) -> None:
        import insightface  # type: ignore
        import onnxruntime  # type: ignore

        if providers is None:
            available = set(onnxruntime.get_available_providers())
            providers = (
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if "CUDAExecutionProvider" in available
                else ["CPUExecutionProvider"]
            )

        # Silence insightface download chatter unless user asked for it.
        os.environ.setdefault("INSIGHTFACE_HOME", str(Path.home() / ".insightface"))

        self.app = insightface.app.FaceAnalysis(
            name=model_name, providers=list(providers)
        )
        self.app.prepare(ctx_id=0, det_size=(det_size, det_size))
        self.providers = list(providers)

    # ------------------------------------------------------------------ #
    def detect(
        self,
        image: np.ndarray,
        frame_index: int = -1,
        crop_margin: float = 0.3,
    ) -> List[DetectedFace]:
        """Detect all faces in a BGR image and return ``DetectedFace`` records."""
        raw = self.app.get(image)
        results: List[DetectedFace] = []
        h, w = image.shape[:2]
        for face in raw:
            x1, y1, x2, y2 = face.bbox.astype(int).tolist()
            # Expand crop a bit so the thumbnail shows more than just the tight box.
            bw, bh = x2 - x1, y2 - y1
            mx, my = int(bw * crop_margin), int(bh * crop_margin)
            cx1 = max(0, x1 - mx)
            cy1 = max(0, y1 - my)
            cx2 = min(w, x2 + mx)
            cy2 = min(h, y2 + my)
            thumb = image[cy1:cy2, cx1:cx2].copy()

            emb = face.normed_embedding.astype(np.float32)
            results.append(
                DetectedFace(
                    frame_index=frame_index,
                    bbox=(x1, y1, x2, y2),
                    det_score=float(face.det_score),
                    embedding=emb,
                    image=thumb,
                )
            )
        return results

    def detect_from_path(self, image_path: str) -> List[DetectedFace]:
        img = cv2.imread(str(image_path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        return self.detect(img, frame_index=-1)
