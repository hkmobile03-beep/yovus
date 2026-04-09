"""Gradio Web UI for the yovus hybrid video face swap tool.

Run:
    python app.py

Then open http://localhost:7860 in your browser.

What it does
------------
1. You upload a target video and a reference face image.
2. The video is transcoded to <= 1080p locally (ffmpeg) before upload,
   so 4K input doesn't blow up your fal bill.
3. Both files are uploaded to fal.ai and the Pixverse Swap endpoint
   (``fal-ai/pixverse/swap``) runs the swap.
4. The swapped video is downloaded back and shown inline.

FAL_KEY is read from the ``.env`` file in this directory (see
``.env.example``) or from the environment.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Iterator, Tuple

# ---------------------------------------------------------------------- #
# Minimal .env loader (same logic as face_swap/cli.py) — runs before any
# code that might touch FAL_KEY.
# ---------------------------------------------------------------------- #
def _load_dotenv() -> None:
    for path in (Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
        return


_load_dotenv()

# ---------------------------------------------------------------------- #
# Logging — use a "yovus" logger so the startup line shows [yovus] INFO ...
# ---------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("yovus")

# ---------------------------------------------------------------------- #
import gradio as gr  # noqa: E402

from face_swap.fal_api import DEFAULT_ENDPOINT, FalFaceSwap  # noqa: E402
from face_swap.video import ensure_max_height, probe  # noqa: E402


# ---------------------------------------------------------------------- #
WORK_ROOT = Path(tempfile.gettempdir()) / "yovus_web"
WORK_ROOT.mkdir(parents=True, exist_ok=True)


def _new_workdir() -> Path:
    d = WORK_ROOT / f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------- #
def swap(
    target_video: str | None,
    source_image: str | None,
    mode: str,
    resolution: str,
    max_height: int,
    keep_audio: bool,
) -> Iterator[Tuple[str, str | None]]:
    """Gradio streaming generator: yields (log_text, output_video_or_None).

    Uses ``yield`` so the UI can show live progress while the job runs.
    """
    lines: list[str] = []

    def emit(msg: str) -> Tuple[str, str | None]:
        log.info(msg)
        lines.append(msg)
        return "\n".join(lines), None

    if not target_video:
        yield emit("error: please upload a target video.")
        return
    if not source_image:
        yield emit("error: please upload a source face image.")
        return
    if not os.environ.get("FAL_KEY"):
        yield emit(
            "error: FAL_KEY is not set. Put it in a .env file in the project "
            "root (see .env.example) or export it before launching app.py."
        )
        return

    workdir = _new_workdir()
    yield emit(f"[job] workdir = {workdir}")

    # ---------- 1. Probe + optional downscale ----------
    try:
        info = probe(target_video)
    except Exception as exc:
        yield emit(f"error: cannot open video: {exc}")
        return
    yield emit(
        f"[target] {Path(target_video).name}  {info.width}x{info.height}  "
        f"{info.fps:.2f} fps  {info.duration_sec:.1f}s"
    )

    try:
        scaled = ensure_max_height(
            target_video,
            str(workdir / f"target_{max_height}p.mp4"),
            max_height=int(max_height),
        )
    except Exception as exc:
        yield emit(f"error: downscale failed: {exc}")
        return

    if Path(scaled).resolve() != Path(target_video).resolve():
        yield emit(f"[preprocess] downscaled to {scaled}")
    else:
        yield emit("[preprocess] video already within max height, no transcode")

    # ---------- 2. Copy source image into the workdir so the path is stable ----------
    src_dst = workdir / ("source" + Path(source_image).suffix)
    shutil.copy2(source_image, src_dst)
    yield emit(f"[source] {src_dst.name}")

    # ---------- 3. Call fal ----------
    try:
        api = FalFaceSwap()
    except RuntimeError as exc:
        yield emit(f"error: {exc}")
        return

    yield emit(f"[cloud] calling fal ({api.endpoint})...")

    # api.run prints progress synchronously via callback. We can't easily
    # stream that into Gradio from inside a blocking call, so we capture
    # each callback message and flush through a shared list after .run
    # returns. For live updates we at least show the pre-call log.
    progress_sink: list[str] = []

    def _progress(msg: str) -> None:
        progress_sink.append(msg)
        log.info("[cloud] %s", msg)

    out_path = workdir / "swapped.mp4"
    try:
        api.run(
            source_image=str(src_dst),
            target_video=str(scaled),
            output_video=str(out_path),
            mode=mode,
            resolution=resolution or None,
            original_sound_switch=bool(keep_audio),
            on_progress=_progress,
        )
    except Exception as exc:
        for m in progress_sink:
            lines.append(f"[cloud] {m}")
        yield emit(f"error: fal call failed: {exc}")
        return

    for m in progress_sink:
        lines.append(f"[cloud] {m}")
    lines.append(f"[done] {out_path}")
    yield "\n".join(lines), str(out_path)


# ---------------------------------------------------------------------- #
def build_ui() -> gr.Blocks:
    with gr.Blocks(title="yovus — video face swap") as demo:
        gr.Markdown(
            "# yovus — video face swap\n"
            f"Cloud endpoint: `{DEFAULT_ENDPOINT}` · "
            "4K input is transcoded to 1080p locally before upload."
        )
        with gr.Row():
            with gr.Column():
                target_video = gr.Video(label="Target video (the video to edit)")
                source_image = gr.Image(
                    label="Source face (the new face)",
                    type="filepath",
                )
                with gr.Row():
                    mode = gr.Dropdown(
                        choices=["person", "object", "background"],
                        value="person",
                        label="Swap mode",
                    )
                    resolution = gr.Dropdown(
                        choices=["", "360p", "540p", "720p", "1080p"],
                        value="",
                        label="Output resolution (blank = auto)",
                    )
                with gr.Row():
                    max_height = gr.Slider(
                        minimum=0,
                        maximum=2160,
                        value=1080,
                        step=10,
                        label="Local max height before upload (0 = disable)",
                    )
                    keep_audio = gr.Checkbox(value=True, label="Keep original audio")
                run_btn = gr.Button("Start face swap", variant="primary")
            with gr.Column():
                log_box = gr.Textbox(
                    label="Progress",
                    lines=20,
                    max_lines=30,
                    interactive=False,
                )
                output_video = gr.Video(label="Swapped video")

        run_btn.click(
            fn=swap,
            inputs=[
                target_video,
                source_image,
                mode,
                resolution,
                max_height,
                keep_audio,
            ],
            outputs=[log_box, output_video],
        )
    return demo


def main() -> None:
    demo = build_ui()
    log.info("Server starting at http://localhost:7860")
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
    )


if __name__ == "__main__":
    main()
