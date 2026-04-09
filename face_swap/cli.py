"""Interactive CLI: local scan → pick identity → pick source → cloud swap.

Workflow
--------
1. Scan the target video locally with InsightFace, sampling ~1 frame/sec.
2. Cluster every detected face into identities (person 0, 1, 2, ...).
3. Write a preview thumbnail for each identity to ``previews/``.
4. Ask which identity the user wants to replace (informational — the fal
   endpoint swaps the dominant face in the video).
5. Scan the source photo folder, pick the clearest face image.
6. If the target video's height > 1080, transcode it to 1080p with ffmpeg.
7. Upload both files to fal and submit the face swap job.
8. Download the result.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

import cv2

from .detector import FaceDetector
from .fal_api import FalFaceSwap
from .identity import Identity, cluster_identities
from .source import pick_best_source_photo
from .video import VideoScanner, ensure_max_height, probe


# ---------------------------------------------------------------------- #
# Minimal .env loader — reads KEY=VALUE pairs into os.environ without
# pulling in python-dotenv. Existing environment variables win over the
# file so you can always override by exporting inline.
# ---------------------------------------------------------------------- #
def _load_dotenv(paths: List[Path]) -> Path | None:
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
        return path
    return None


# ---------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yovus-faceswap",
        description=(
            "Hybrid video face swap — identify people locally, swap via fal.ai."
        ),
    )
    parser.add_argument("-t", "--target", required=True,
                        help="Target video to edit.")
    parser.add_argument("-s", "--source-folder", required=True,
                        help="Folder of reference photos of the new person.")
    parser.add_argument("-o", "--output", required=True,
                        help="Where to save the swapped video.")
    parser.add_argument("--previews-dir", default="previews",
                        help="Directory for detected-identity thumbnails "
                             "(default: ./previews).")
    parser.add_argument("--max-height", type=int, default=1080,
                        help="Downscale target video to at most this height "
                             "before uploading (default: 1080). Use 0 or a "
                             "negative value to disable the downscale step.")
    parser.add_argument("--sample-fps", type=float, default=1.0,
                        help="Frames per second to sample during local scan "
                             "(default: 1.0).")
    parser.add_argument("--similarity", type=float, default=0.45,
                        help="Cosine similarity threshold for identity "
                             "clustering (default: 0.45).")
    parser.add_argument("--mode", default="person",
                        choices=("person", "object", "background"),
                        help="Pixverse swap mode (default: person). "
                             "Ignored when --endpoint=halfmoon.")
    parser.add_argument("--resolution", default=None,
                        choices=("360p", "540p", "720p", "1080p"),
                        help="Optional output resolution for the swap "
                             "(pixverse only).")
    parser.add_argument("--endpoint", default="pixverse",
                        choices=("pixverse", "halfmoon"),
                        help="Which fal endpoint to use. 'pixverse' "
                             "(default) = fal-ai/pixverse/swap, fast and "
                             "robust but regenerates more than the face. "
                             "'halfmoon' = half-moon-ai/ai-face-swap/"
                             "faceswapvideo, face-only swap that preserves "
                             "clothes — try this if pixverse drifts across "
                             "scenes.")
    parser.add_argument("--keyframe", type=int, default=None,
                        help="Pixverse keyframe_id. Set to 1 to anchor the "
                             "swap to the first frame and reduce drift "
                             "across long videos (pixverse only).")
    parser.add_argument("--keep-audio", dest="keep_audio",
                        action="store_true", default=True,
                        help="Preserve the original audio track (default).")
    parser.add_argument("--no-audio", dest="keep_audio",
                        action="store_false",
                        help="Drop the original audio track.")
    parser.add_argument("--yes", action="store_true",
                        help="Do not prompt; auto-pick the most-prominent "
                             "identity and proceed.")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU execution for local detection.")
    parser.add_argument("--det-size", type=int, default=640,
                        help="Face detector input size (default: 640).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan + show identities + pick source, but do "
                             "not call the fal API.")
    return parser


# ---------------------------------------------------------------------- #
def _write_identity_previews(
    identities: List[Identity], previews_dir: Path
) -> List[Path]:
    previews_dir.mkdir(parents=True, exist_ok=True)
    for existing in previews_dir.glob("person_*.jpg"):
        existing.unlink()

    written: List[Path] = []
    for ident in identities:
        face = ident.best_face
        path = previews_dir / f"person_{ident.index:02d}.jpg"
        if face.image.size > 0:
            cv2.imwrite(str(path), face.image)
            written.append(path)
    return written


def _prompt_identity(identities: List[Identity]) -> Identity:
    while True:
        try:
            choice = input(
                f"Pick identity to replace [0-{len(identities) - 1}, default 0]: "
            ).strip()
        except EOFError:
            return identities[0]
        if not choice:
            return identities[0]
        if choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(identities):
                return identities[idx]
        print("  invalid choice, try again.")


# ---------------------------------------------------------------------- #
def main(argv: List[str] | None = None) -> int:
    # Load .env from the current working dir or the project root before we
    # touch any env-dependent code. Existing env vars always win.
    here = Path(__file__).resolve().parent.parent
    loaded = _load_dotenv([Path.cwd() / ".env", here / ".env"])
    if loaded is not None:
        print(f"[env] loaded {loaded}")

    args = build_parser().parse_args(argv)

    target_path = Path(args.target)
    if not target_path.is_file():
        print(f"error: target video not found: {target_path}", file=sys.stderr)
        return 2

    # ---------------- 1. Probe + detector ---------------- #
    info = probe(str(target_path))
    print(
        f"[target] {info.path.name}  {info.width}x{info.height}  "
        f"{info.fps:.2f} fps  {info.duration_sec:.1f}s"
    )

    providers = ["CPUExecutionProvider"] if args.cpu else None
    print("[local] loading InsightFace (buffalo_l)...")
    detector = FaceDetector(det_size=args.det_size, providers=providers)

    # ---------------- 2. Scan target video ---------------- #
    scanner = VideoScanner(detector, sample_fps=args.sample_fps)
    print(f"[local] scanning video at {args.sample_fps} fps sample rate...")
    _, faces = scanner.scan(str(target_path))
    print(f"[local] detected {len(faces)} face instances across sampled frames")

    if not faces:
        print("error: no faces detected in the target video.", file=sys.stderr)
        return 1

    # ---------------- 3. Cluster into identities ---------------- #
    identities = cluster_identities(faces, similarity_threshold=args.similarity)
    print(f"[local] found {len(identities)} distinct identities:")
    previews_dir = Path(args.previews_dir)
    previews = _write_identity_previews(identities, previews_dir)
    for ident, preview in zip(identities, previews):
        print(
            f"  person_{ident.index:02d}  "
            f"appears in {ident.count} sampled frames  "
            f"preview: {preview}"
        )

    # ---------------- 4. Pick identity ---------------- #
    if args.yes:
        chosen = identities[0]
        print(f"[local] --yes: auto-selecting person_{chosen.index:02d}")
    else:
        print(
            "\nOpen the preview thumbnails in the previews folder to see who "
            "is who, then choose."
        )
        chosen = _prompt_identity(identities)
    print(f"[local] will replace person_{chosen.index:02d}")

    # ---------------- 5. Pick source photo ---------------- #
    print(f"[local] scanning source photo folder: {args.source_folder}")
    src_photo, src_face = pick_best_source_photo(args.source_folder, detector)
    print(
        f"[local] best source photo: {src_photo}  "
        f"(face area={src_face.area}, det_score={src_face.det_score:.2f})"
    )

    if args.dry_run:
        print("[dry-run] stopping before cloud call.")
        return 0

    # ---------------- 6. Downscale if needed ---------------- #
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    scaled_target = ensure_max_height(
        str(target_path),
        str(tmp_dir / f"{target_path.stem}_{args.max_height}p.mp4"),
        max_height=args.max_height,
    )
    if scaled_target.resolve() != target_path.resolve():
        print(f"[preprocess] using downscaled copy: {scaled_target}")

    # ---------------- 7. Call fal ---------------- #
    try:
        api = FalFaceSwap(preset=args.endpoint)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"[cloud] calling fal ({api.endpoint})...")
    try:
        out_path = api.run(
            source_image=str(src_photo),
            target_video=str(scaled_target),
            output_video=args.output,
            mode=args.mode,
            resolution=args.resolution,
            original_sound_switch=args.keep_audio,
            keyframe_id=args.keyframe,
            on_progress=lambda msg: print(f"[cloud] {msg}"),
        )
    except Exception as exc:  # pragma: no cover — network / API errors
        print(f"error: fal call failed: {exc}", file=sys.stderr)
        return 1

    print(f"\nDone. Output: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
