"""Thin wrapper around the fal.ai Python client for the video face swap API.

Endpoint: ``half-moon-ai/ai-face-swap/faceswapvideo`` (video-to-video).

Auth:
    Set the ``FAL_KEY`` environment variable to your fal.ai API key.

Input parameters accepted by the endpoint:
    - ``source_face_url``   (str, required)  reference face image URL
    - ``target_video_url``  (str, required)  target video URL
    - ``occlusion``         (bool, optional) enable occlusion-aware model (2x cost)

Notes:
    - Target video is capped at 25 minutes (longer is truncated).
    - Target FPS is capped at 25 by the provider.
    - Supported target formats: avi, m4v, mkv, mp4, mpeg, mov, mxf, webm, wmv.
    - Supported source image formats: bmp, jpeg, png, tiff, webp.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

DEFAULT_ENDPOINT = "half-moon-ai/ai-face-swap/faceswapvideo"


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
        endpoint: str = DEFAULT_ENDPOINT,
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
        self.endpoint = endpoint

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
    def submit(
        self,
        source_face_url: str,
        target_video_url: str,
        occlusion: bool = False,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Submit a synchronous face-swap job and return the result dict.

        Uses ``fal_client.subscribe`` which blocks until completion and
        streams progress events back through ``on_progress``.
        """
        arguments: Dict[str, Any] = {
            "source_face_url": source_face_url,
            "target_video_url": target_video_url,
        }
        if occlusion:
            arguments["occlusion"] = True

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
        occlusion: bool = False,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Path:
        """End-to-end helper: upload inputs, submit, download output."""
        if on_progress:
            on_progress(f"uploading source image: {source_image}")
        source_url = self.upload(source_image)
        if on_progress:
            on_progress(f"uploading target video: {target_video}")
        video_url = self.upload(target_video)
        if on_progress:
            on_progress("submitting job to fal…")
        result = self.submit(
            source_face_url=source_url,
            target_video_url=video_url,
            occlusion=occlusion,
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
