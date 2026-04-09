"""Pick the best reference face image from a folder of photos."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2

from .detector import DetectedFace, FaceDetector


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp",
}


def list_photos(folder: str) -> List[Path]:
    root = Path(folder)
    if not root.exists():
        raise FileNotFoundError(f"Source photo folder not found: {root}")
    if root.is_file():
        return [root]
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def _score_face(face: DetectedFace) -> float:
    """Bigger face + higher det score is better."""
    return face.area * face.det_score


def pick_best_source_photo(
    folder: str,
    detector: FaceDetector,
) -> Tuple[Path, DetectedFace]:
    """Scan every image in ``folder`` and return the (photo path, face)
    with the largest, most confidently detected frontal-ish face.

    The photo path is what you upload to the cloud API as the source face
    reference. If more than one face is found in a photo, the largest is
    used to score the photo (but the entire photo is still uploaded — the
    cloud model picks the dominant face).
    """
    photos = list_photos(folder)
    if not photos:
        raise RuntimeError(f"No images found in {folder}")

    best: Optional[Tuple[Path, DetectedFace, float]] = None
    for photo in photos:
        img = cv2.imread(str(photo))
        if img is None:
            continue
        faces = detector.detect(img, frame_index=-1)
        if not faces:
            continue
        face = max(faces, key=_score_face)
        score = _score_face(face)
        if best is None or score > best[2]:
            best = (photo, face, score)

    if best is None:
        raise RuntimeError(
            f"No faces detected in any photo under {folder}. "
            "Check the folder contains clear portraits."
        )
    return best[0], best[1]
