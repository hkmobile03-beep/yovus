"""
High-quality video face swap using Facefusion.

Replaces every face in a video with the face from a reference photo. Uses
inswapper_128_fp16 for swapping + GFPGAN/CodeFormer for face enhancement +
occlusion masking + temporal smoothing. This is the recommended pipeline for
the YOVUS "replace the model in my existing videos" workflow.

Prerequisite:
  python scripts/setup_facefusion.py

Usage:
  python scripts/video_faceswap_pro.py <input_video> <reference_photo_or_folder>
  python scripts/video_faceswap_pro.py in.mp4 C:\\Users\\junqi\\Desktop\\test
  python scripts/video_faceswap_pro.py in.mp4 ref.jpg --output out.mp4
  python scripts/video_faceswap_pro.py in.mp4 ref.jpg --enhancer codeformer
  python scripts/video_faceswap_pro.py in.mp4 ref.jpg --cpu         # fallback
  python scripts/video_faceswap_pro.py in.mp4 ref.jpg --no-enhance  # faster
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FACEFUSION_DIR = PROJECT_ROOT / "external" / "facefusion"

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def pick_best_reference(ref: Path) -> Path:
    """If ref is a folder, pick the highest-resolution photo inside."""
    if ref.is_file():
        return ref

    if not ref.is_dir():
        print(f"  ERROR: reference path not found: {ref}")
        sys.exit(1)

    photos = [p for p in ref.iterdir() if p.suffix.lower() in PHOTO_EXTS]
    if not photos:
        print(f"  ERROR: no photos in {ref}")
        sys.exit(1)

    # Biggest file usually = highest resolution = best identity capture.
    # Facefusion only needs a single clear source image to lock the face.
    best = max(photos, key=lambda p: p.stat().st_size)
    size_kb = best.stat().st_size // 1024
    print(f"  Auto-picked reference: {best.name} ({size_kb} KB)")
    print(f"  (From {len(photos)} photos in folder)")
    return best


def default_output_path(input_video: Path) -> Path:
    out_dir = PROJECT_ROOT / "output" / "video_swap"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{input_video.stem}_swapped{input_video.suffix}"


def build_facefusion_cmd(args, source: Path, target: Path, output: Path):
    processors = ["face_swapper"]
    if not args.no_enhance:
        processors.append("face_enhancer")

    cmd = [
        sys.executable, "facefusion.py", "headless-run",
        "--source-paths", str(source.resolve()),
        "--target-path", str(target.resolve()),
        "--output-path", str(output.resolve()),
        "--processors", *processors,
        "--face-swapper-model", args.swapper_model,
        "--execution-providers", args.provider,
        "--output-video-encoder", "libx264",
        "--output-video-quality", str(args.quality),
        "--face-detector-model", "yoloface",
        "--face-selector-mode", "reference",
    ]

    if not args.no_enhance:
        cmd.extend([
            "--face-enhancer-model", args.enhancer,
            "--face-enhancer-blend", str(args.enhancer_blend),
        ])

    if args.extra:
        # Allow pass-through args: --extra="--face-mask-blur 0.5 --trim-frame-end 300"
        cmd.extend(args.extra.split())

    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="High-quality video face swap via Facefusion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_video", help="Path to input video (mp4/mov/mkv/...)")
    parser.add_argument(
        "reference",
        help="Reference photo (single file) OR folder with multiple photos "
             "(script auto-picks the largest)",
    )
    parser.add_argument("--output", "-o", help="Output video path (default: output/video_swap/<name>_swapped.mp4)")
    parser.add_argument(
        "--provider",
        default="cuda",
        choices=["cuda", "cpu", "directml", "openvino", "rocm"],
        help="Execution provider (default: cuda)",
    )
    parser.add_argument("--cpu", action="store_true", help="Shortcut for --provider cpu")
    parser.add_argument(
        "--swapper-model",
        default="inswapper_128_fp16",
        choices=["inswapper_128", "inswapper_128_fp16", "simswap_256", "simswap_512_unofficial",
                 "uniface_256", "blendswap_256"],
        help="Face swap model (default: inswapper_128_fp16)",
    )
    parser.add_argument(
        "--enhancer",
        default="gfpgan_1.4",
        choices=["gfpgan_1.4", "gfpgan_1.3", "gfpgan_1.2",
                 "codeformer", "gpen_bfr_256", "gpen_bfr_512",
                 "gpen_bfr_1024", "gpen_bfr_2048", "restoreformer_plus_plus"],
        help="Face enhancer model (default: gfpgan_1.4)",
    )
    parser.add_argument(
        "--enhancer-blend",
        type=int,
        default=80,
        help="Enhancer blend strength 0-100 (default: 80)",
    )
    parser.add_argument("--no-enhance", action="store_true", help="Skip face enhancement (faster)")
    parser.add_argument("--quality", type=int, default=90, help="Output video quality 0-100 (default: 90)")
    parser.add_argument("--extra", default="", help="Extra args passed verbatim to facefusion")

    args = parser.parse_args()

    if args.cpu:
        args.provider = "cpu"

    if not FACEFUSION_DIR.exists():
        print("  ERROR: Facefusion not installed.")
        print(f"  Expected at: {FACEFUSION_DIR}")
        print("  Run: python scripts/setup_facefusion.py")
        sys.exit(1)

    input_video = Path(args.input_video)
    if not input_video.exists():
        print(f"  ERROR: video not found: {input_video}")
        sys.exit(1)
    if input_video.suffix.lower() not in VIDEO_EXTS:
        print(f"  WARNING: unusual video extension: {input_video.suffix}")

    source = pick_best_reference(Path(args.reference))
    output = Path(args.output) if args.output else default_output_path(input_video)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_facefusion_cmd(args, source, input_video, output)

    print()
    print("=" * 60)
    print("  Facefusion Video Face Swap")
    print("=" * 60)
    print(f"  Source photo : {source}")
    print(f"  Target video : {input_video}")
    print(f"  Output video : {output}")
    print(f"  Provider     : {args.provider}")
    print(f"  Swapper      : {args.swapper_model}")
    if args.no_enhance:
        print(f"  Enhancer     : (disabled)")
    else:
        print(f"  Enhancer     : {args.enhancer} @ blend={args.enhancer_blend}")
    print("=" * 60)
    print()
    print("  First run will download models (~2GB) to ~/.facefusion")
    print("  Processing... this may take several minutes depending on video length.")
    print()

    result = subprocess.run(cmd, cwd=FACEFUSION_DIR)
    if result.returncode != 0:
        print()
        print(f"  ERROR: facefusion exited with code {result.returncode}")
        print("  Common causes:")
        print("    - CUDA/driver mismatch -> retry with --cpu")
        print("    - Out of VRAM -> retry with --cpu or use smaller video")
        print("    - Model download failed -> check internet")
        sys.exit(result.returncode)

    if not output.exists():
        print(f"\n  ERROR: facefusion reported success but output not found: {output}")
        sys.exit(1)

    size_mb = output.stat().st_size / 1024 / 1024
    print()
    print("=" * 60)
    print(f"  DONE  ->  {output}")
    print(f"  Size  ->  {size_mb:.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
