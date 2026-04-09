"""Thin wrapper around the fal.ai Python client for video face swap.

Two presets are supported, selectable via the ``preset`` kwarg:

- ``pixverse`` (default) — ``fal-ai/pixverse/swap``
    Pixverse's keyframe-based swap. In ``person`` mode it regenerates more
    than the face (including clothes/hair detail) and can drift across
    long videos. A ``keyframe_id`` can be supplied to anchor the swap to
    a specific frame.

- ``halfmoon`` — ``half-moon-ai/ai-face-swap/faceswapvideo``
    Face-only swap. Keeps clothes and body intact. Slower / rarer on
    fal's infra; returns "Application not found" if fal routing is
    flaky — in that case fall back to ``pixverse``.

Auth:
    Set the ``FAL_KEY`` environment variable to your fal.ai API key.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

PIXVERSE_ENDPOINT = "fal-ai/pixverse/swap"
HALFMOON_ENDPOINT = "half-moon-ai/ai-face-swap/faceswapvideo"
DEFAULT_ENDPOINT = PIXVERSE_ENDPOINT

PRESETS: Dict[str, str] = {
    "pixverse": PIXVERSE_ENDPOINT,
    "halfmoon": HALFMOON_ENDPOINT,
}


class FalFaceSwap:
    """High-level wrapper: upload files, submit job, download result.

    Example
    -------
    >>> api = FalFaceSwap()                       # reads FAL_KEY env var
    >>> out = api.run(
    ...     source_image="face.jpg",
    ...     target_video="scene_1080p.mp4",
    ...     output_video="scene_swapped.mp4",
    ... )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        preset: str = "pixverse",
        endpoint: Optional[str] = None,
    ) -> None:
        if api_key:
            os.environ["FAL_KEY"] = api_key
        if not os.environ.get("FAL_KEY"):
            raise RuntimeError(
                "FAL_KEY environment variable is not set. "
                "Export it or pass api_key= to FalFaceSwap()."
            )

        # Lazy import so `--help` and dry-run work without the dep installed.
        try:
            import fal_client  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "fal-client is not installed. Run "
                "`pip install -r requirements.txt` (or `pip install fal-client`)."
            ) from exc

        self._fal = fal_client
        if preset not in PRESETS:
            raise ValueError(
                f"Unknown preset {preset!r}. Choose one of {list(PRESETS)}."
            )
        self.preset = preset
        self.endpoint = endpoint or PRESETS[preset]

    # ------------------------------------------------------------------ #
    def upload(self, path: str) -> str:
        """Upload a local file to fal storage and return a public URL."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Cannot upload — file not found: {p}")
        url = self._fal.upload_file(str(p))
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise RuntimeError(
                f"fal_client.upload_file returned an unexpected value for "
                f"{p}: {url!r}"
            )
        return url

    # ------------------------------------------------------------------ #
    def _build_arguments(
        self,
        image_url: str,
        video_url: str,
        mode: str,
        resolution: Optional[str],
        original_sound_switch: Optional[bool],
        keyframe_id: Optional[int],
    ) -> Dict[str, Any]:
        """Shape the request body based on the active preset."""
        if self.preset == "halfmoon":
            args: Dict[str, Any] = {
                "source_face_url": image_url,
                "target_video_url": video_url,
            }
            return args

        # Default / pixverse
        args = {
            "video_url": video_url,
            "image_url": image_url,
            "mode": mode,
        }
        if resolution:
            args["resolution"] = resolution
        if original_sound_switch is not None:
            args["original_sound_switch"] = original_sound_switch
        if keyframe_id is not None:
            args["keyframe_id"] = keyframe_id
        return args

    # ------------------------------------------------------------------ #
    def submit(
        self,
        image_url: str,
        video_url: str,
        mode: str = "person",
        resolution: Optional[str] = None,
        original_sound_switch: Optional[bool] = None,
        keyframe_id: Optional[int] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Submit a synchronous face-swap job and return the result dict."""
        arguments = self._build_arguments(
            image_url=image_url,
            video_url=video_url,
            mode=mode,
            resolution=resolution,
            original_sound_switch=original_sound_switch,
            keyframe_id=keyframe_id,
        )

        def _on_update(update: Any) -> None:
            if on_progress is None:
                return
            logs = getattr(update, "logs", None)
            if logs:
                for entry in logs:
                    msg = entry.get("message") if isinstance(entry, dict) else str(entry)
                    if msg:
                        on_progress(msg)

        result = self._fal.subscribe(
            self.endpoint,
            arguments=arguments,
            with_logs=True,
            on_queue_update=_on_update,
        )
        return result

    # ------------------------------------------------------------------ #
    def download_result(self, result: Dict[str, Any], output_video: str) -> Path:
        """Extract the output video URL from a fal result and save it locally."""
        import requests

        video_url = _extract_video_url(result)
        if not video_url:
            raise RuntimeError(f"No video URL in fal result: {result!r}")

        dst = Path(output_video)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(video_url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with dst.open("wb") as f:
                shutil.copyfileobj(r.raw, f)
        return dst

    # ------------------------------------------------------------------ #
    def run(
        self,
        source_image: str,
        target_video: str,
        output_video: str,
        mode: str = "person",
        resolution: Optional[str] = None,
        original_sound_switch: Optional[bool] = None,
        keyframe_id: Optional[int] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Path:
        """End-to-end helper: upload inputs, submit, download output."""
        if on_progress:
            on_progress(f"uploading source image: {source_image}")
        image_url = self.upload(source_image)
        if on_progress:
            on_progress(f"uploading target video: {target_video}")
        video_url = self.upload(target_video)
        if on_progress:
            on_progress(f"submitting job to fal ({self.endpoint})…")
        result = self.submit(
            image_url=image_url,
            video_url=video_url,
            mode=mode,
            resolution=resolution,
            original_sound_switch=original_sound_switch,
            keyframe_id=keyframe_id,
            on_progress=on_progress,
        )
        if on_progress:
            on_progress(f"downloading result to {output_video}")
        return self.download_result(result, output_video)


# ---------------------------------------------------------------------- #
def _extract_video_url(result: Dict[str, Any]) -> Optional[str]:
    """Robustly find the output video URL in fal's result payload.

    fal endpoints vary in response shape — sometimes ``{"video": {"url": ...}}``,
    sometimes ``{"output": {...}}``, sometimes just ``{"url": ...}``. This
    function walks the payload looking for any ``.mp4``/``.webm``/``.mov``
    URL it can find.
    """
    if not isinstance(result, dict):
        return None

    def _walk(obj: Any) -> Optional[str]:
        if isinstance(obj, str):
            lower = obj.lower()
            if lower.startswith("http") and any(
                lower.endswith(ext) or (ext + "?") in lower
                for ext in (".mp4", ".webm", ".mov", ".mkv")
            ):
                return obj
            return None
        if isinstance(obj, dict):
            # Prefer explicit keys first.
            for key in ("video", "output", "result"):
                if key in obj:
                    found = _walk(obj[key])
                    if found:
                        return found
            if "url" in obj and isinstance(obj["url"], str):
                return obj["url"]
            for v in obj.values():
                found = _walk(v)
                if found:
                    return found
        if isinstance(obj, list):
            for item in obj:
                found = _walk(item)
                if found:
                    return found
        return None

    return _walk(result)
