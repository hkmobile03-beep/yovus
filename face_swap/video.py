"""Video sampling (for local face scan) and ffmpeg-based 1080p downscale."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import cv2
import numpy as np
from tqdm import tqdm

from .detector import DetectedFace, FaceDetector


# ---------------------------------------------------------------------- #
# Video metadata
# ---------------------------------------------------------------------- #
@dataclass
class VideoInfo:
    path: Path
    width: int
    height: int
    fps: float
    frame_count: int
    duration_sec: float


def probe(video_path: str) -> VideoInfo:
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {path}")
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()
    duration = count / fps if fps > 0 else 0.0
    return VideoInfo(path, width, height, fps, count, duration)


# ---------------------------------------------------------------------- #
# Frame sampling for face scanning
# ---------------------------------------------------------------------- #
class VideoScanner:
    """Sample frames from a video and run ``FaceDetector`` over them.

    We do NOT process every frame (too slow on long / high-res videos). Instead
    we sample at a fixed temporal rate (``sample_fps``, default 1 FPS). That is
    plenty to catch every identity that appears.
    """

    def __init__(
        self,
        detector: FaceDetector,
        sample_fps: float = 1.0,
        max_samples: Optional[int] = None,
    ) -> None:
        self.detector = detector
        self.sample_fps = sample_fps
        self.max_samples = max_samples

    def _iter_sample_frames_with_info(
        self, info: VideoInfo
    ) -> Iterator[Tuple[int, np.ndarray]]:
        cap = cv2.VideoCapture(str(info.path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {info.path}")

        stride = max(1, int(round(info.fps / self.sample_fps))) if info.fps > 0 else 1
        try:
            idx = 0
            emitted = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % stride == 0:
                    yield idx, frame
                    emitted += 1
                    if self.max_samples is not None and emitted >= self.max_samples:
                        break
                idx += 1
        finally:
            cap.release()

    def iter_sample_frames(
        self, video_path: str
    ) -> Iterator[Tuple[int, np.ndarray]]:
        """Public iterator — probes the video path and yields sampled frames."""
        info = probe(video_path)
        yield from self._iter_sample_frames_with_info(info)

    def scan(self, video_path: str) -> Tuple[VideoInfo, List[DetectedFace]]:
        info = probe(video_path)
        if info.frame_count <= 0 or info.fps <= 0:
            raise RuntimeError(
                f"Video has no readable frames (fps={info.fps}, "
                f"frame_count={info.frame_count}): {info.path}"
            )

        total_samples: Optional[int] = None
        if info.duration_sec:
            total_samples = max(1, int(info.duration_sec * self.sample_fps))
        if self.max_samples is not None:
            total_samples = (
                min(total_samples, self.max_samples)
                if total_samples is not None
                else self.max_samples
            )

        all_faces: List[DetectedFace] = []
        progress = tqdm(
            total=total_samples,
            desc="Scanning faces",
            unit="frame",
            leave=False,
        )
        try:
            for frame_idx, frame in self._iter_sample_frames_with_info(info):
                faces = self.detector.detect(frame, frame_index=frame_idx)
                all_faces.extend(faces)
                progress.update(1)
        finally:
            progress.close()
        return info, all_faces


# ---------------------------------------------------------------------- #
# 1080p downscale (ffmpeg)
# ---------------------------------------------------------------------- #
def _ffmpeg_binary() -> str:
    """Return a usable ffmpeg binary path. Prefers the system ffmpeg; falls
    back to the one shipped with ``imageio-ffmpeg``."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "ffmpeg not found. Install ffmpeg or `pip install imageio-ffmpeg`."
        ) from exc


def ensure_max_height(
    input_video: str,
    output_video: str,
    max_height: int = 1080,
    crf: int = 18,
    max_dim: int = 1920,
) -> Path:
    """Re-encode ``input_video`` so it fits within both height and max-dim
    limits while preserving aspect ratio.

    Two constraints are applied together:

    - ``max_height``  : the output height must be <= this value (<=0 disables)
    - ``max_dim``     : neither width nor height may exceed this value; this
                        matters for ultra-wide sources where scaling by height
                        alone would still leave the width too large. The fal
                        Pixverse Swap endpoint rejects anything with a side
                        longer than 1920, hence the default. (<=0 disables)

    The source file is returned as-is if both constraints are already
    satisfied, or if both constraints are disabled. Otherwise ffmpeg
    transcodes to H.264 + AAC at an exact, even width/height that honors
    both caps.
    """
    src = Path(input_video)
    if max_height <= 0 and max_dim <= 0:
        return src

    info = probe(str(src))
    w, h = info.width, info.height
    if w <= 0 or h <= 0:
        raise RuntimeError(f"Invalid video dimensions {w}x{h} in {src}")

    # Work out the largest scale factor that still honors both caps.
    scale = 1.0
    if max_height > 0 and h > max_height:
        scale = min(scale, max_height / h)
    if max_dim > 0 and max(w, h) * scale > max_dim:
        scale = min(scale, max_dim / max(w, h))

    if scale >= 1.0:
        # already within both limits — no transcode needed
        return src

    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    # libx264 + yuv420p requires even dimensions
    new_w -= new_w % 2
    new_h -= new_h % 2

    dst = Path(output_video)
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_binary()
    vf = f"scale={new_w}:{new_h}"
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(dst),
    ]
    print(
        f"[preprocess] downscaling {w}x{h} -> {new_w}x{new_h} "
        f"(max_height={max_height}, max_dim={max_dim})..."
    )
    subprocess.run(cmd, check=True)
    return dst
