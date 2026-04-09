"""
Run Facefusion's face enhancer on a video to sharpen faces. Use this on the
output of cloud_video_swap.py when the swapped result looks soft/blurry:
the swapper creates a 128x128 face region which Fal/pixverse do not strongly
enhance, so running GFPGAN/CodeFormer on top often recovers detail.

Prereq:
  python scripts/setup_facefusion.py

Usage:
  python scripts/enhance_video_faces.py <input_video>
  python scripts/enhance_video_faces.py <input_video> -o <output>
  python scripts/enhance_video_faces.py <input_video> --enhancer codeformer
  python scripts/enhance_video_faces.py <input_video> --cpu
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
FACEFUSION_DIR = PROJECT_ROOT / "external" / "facefusion"


def default_output(video: Path) -> Path:
    out_dir = PROJECT_ROOT / "output" / "enhanced"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{video.stem}_enhanced{video.suffix}"


def main():
    parser = argparse.ArgumentParser(description="Sharpen faces in a video via Facefusion")
    parser.add_argument("input_video", help="Video to enhance (typically the cloud-swapped output)")
    parser.add_argument("--output", "-o", help="Output path (default: output/enhanced/<name>_enhanced.<ext>)")
    parser.add_argument(
        "--enhancer",
        default="gfpgan_1.4",
        choices=["gfpgan_1.4", "gfpgan_1.3", "codeformer",
                 "gpen_bfr_512", "gpen_bfr_1024", "gpen_bfr_2048",
                 "restoreformer_plus_plus"],
        help="Face enhancer model (default: gfpgan_1.4)",
    )
    parser.add_argument("--blend", type=int, default=90, help="Enhancer blend 0-100 (default: 90)")
    parser.add_argument("--provider", default="cuda",
                        choices=["cuda", "cpu", "directml", "openvino", "rocm"])
    parser.add_argument("--cpu", action="store_true", help="Shortcut for --provider cpu")
    parser.add_argument("--quality", type=int, default=95, help="Output video quality 0-100 (default: 95)")

    args = parser.parse_args()
    if args.cpu:
        args.provider = "cpu"

    if not FACEFUSION_DIR.exists():
        print("  ERROR: Facefusion not installed.")
        print(f"  Expected at: {FACEFUSION_DIR}")
        print("  Run: python scripts/setup_facefusion.py")
        sys.exit(1)

    video = Path(args.input_video)
    if not video.exists():
        print(f"  ERROR: video not found: {video}")
        sys.exit(1)

    output = Path(args.output) if args.output else default_output(video)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "facefusion.py", "headless-run",
        "--target-path", str(video.resolve()),
        "--output-path", str(output.resolve()),
        "--processors", "face_enhancer",
        "--face-enhancer-model", args.enhancer,
        "--face-enhancer-blend", str(args.blend),
        "--execution-providers", args.provider,
        "--output-video-encoder", "libx264",
        "--output-video-quality", str(args.quality),
        "--face-detector-model", "yoloface",
    ]

    print()
    print("=" * 60)
    print("  Facefusion Face Enhancement (no swap)")
    print("=" * 60)
    print(f"  Input        : {video}")
    print(f"  Output       : {output}")
    print(f"  Enhancer     : {args.enhancer} @ blend={args.blend}")
    print(f"  Provider     : {args.provider}")
    print("=" * 60)
    print()

    result = subprocess.run(cmd, cwd=FACEFUSION_DIR)
    if result.returncode != 0:
        print(f"\n  ERROR: facefusion exited with code {result.returncode}")
        print("  Try --cpu if this was a GPU/VRAM failure.")
        sys.exit(result.returncode)

    if not output.exists():
        print(f"\n  ERROR: output not produced at {output}")
        sys.exit(1)

    size_mb = output.stat().st_size / 1024 / 1024
    print()
    print("=" * 60)
    print(f"  DONE  ->  {output}")
    print(f"  Size  ->  {size_mb:.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
