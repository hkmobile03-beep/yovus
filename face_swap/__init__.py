"""Hybrid video face swap: local face detection + fal.ai cloud swap."""

from .detector import FaceDetector, DetectedFace
from .identity import Identity, cluster_identities
from .video import VideoScanner, ensure_max_height
from .source import pick_best_source_photo
from .fal_api import FalFaceSwap

__all__ = [
    "FaceDetector",
    "DetectedFace",
    "Identity",
    "cluster_identities",
    "VideoScanner",
    "ensure_max_height",
    "pick_best_source_photo",
    "FalFaceSwap",
]
__version__ = "0.2.0"
