"""
Cloud video face swap via Fal.ai (Half-Moon AI model).

Replaces every face in a video with the face from a reference photo, using
the half-moon-ai/ai-face-swap/faceswapvideo endpoint on Fal.ai. This is the
cheap + fast cloud alternative to running Facefusion locally.

Auth:
  Set FAL_KEY environment variable. NEVER hardcode the key.
    PowerShell (temp):  $env:FAL_KEY = "your_key"
    PowerShell (perm):  [Environment]::SetEnvironmentVariable("FAL_KEY","your_key","User")

Usage:
  python scripts/cloud_video_swap.py <input_video> <reference_photo_or_folder>
  python scripts/cloud_video_swap.py in.mp4 C:\\Users\\junqi\\Desktop\\test
  python scripts/cloud_video_swap.py in.mp4 ref.jpg --output out.mp4
  python scripts/cloud_video_swap.py in.mp4 ref.jpg --test-image-only   # cheap test: 1 image swap

Notes:
  - Fal.ai caps target video at 25 minutes / 25 fps (they will truncate/downsample)
  - Source photo formats: jpg/jpeg/png/bmp/tiff/webp
  - Keep the source photo a clear frontal face, high resolution
"""
import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

ENDPOINT_VIDEO = "half-moon-ai/ai-face-swap/faceswapvideo"
ENDPOINT_IMAGE = "half-moon-ai/ai-face-swap/faceswapimage"


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

    best = max(photos, key=lambda p: p.stat().st_size)
    size_kb = best.stat().st_size // 1024
    print(f"  Auto-picked reference: {best.name} ({size_kb} KB) from {len(photos)} photos")
    return best


def default_output(input_path: Path, is_image: bool) -> Path:
    if is_image:
        out_dir = PROJECT_ROOT / "output" / "cloud_image_swap"
        suffix = ".png"
    else:
        out_dir = PROJECT_ROOT / "output" / "cloud_video_swap"
        suffix = input_path.suffix or ".mp4"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{input_path.stem}_swapped{suffix}"


def require_fal_client():
    try:
        import fal_client  # noqa: F401
        return fal_client
    except ImportError:
        print("  ERROR: fal_client not installed")
        print("  Run: pip install fal-client")
        sys.exit(1)


def require_api_key():
    key = os.environ.get("FAL_KEY", "").strip()
    if not key:
        print("  ERROR: FAL_KEY environment variable not set")
        print()
        print("  Set it in PowerShell:")
        print('    $env:FAL_KEY = "your_key"                                              # current session')
        print('    [Environment]::SetEnvironmentVariable("FAL_KEY","your_key","User")     # persistent')
        print()
        print("  Get your key at: https://fal.ai/dashboard/keys")
        sys.exit(1)
    return key


def download_output(url: str, output_path: Path):
    import httpx
    print(f"  Downloading result: {url[:80]}...")
    with httpx.stream("GET", url, timeout=300, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  Saved: {output_path} ({size_mb:.1f} MB)")


def run_image_test(fal_client, source: Path, target_video: Path, output: Path):
    """Cheap sanity test: extract 1 frame from the video and swap as an image."""
    import subprocess
    import tempfile

    print("\n  [test mode] Extracting first frame of video for cheap image-swap test...")
    tmp_frame = Path(tempfile.gettempdir()) / f"yovus_test_frame_{target_video.stem}.png"
    cmd = ["ffmpeg", "-y", "-i", str(target_video), "-vframes", "1", "-q:v", "2", str(tmp_frame)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not tmp_frame.exists():
        print(f"  ERROR: ffmpeg failed to extract frame: {result.stderr[:200]}")
        sys.exit(1)

    print(f"  Uploading source photo ...")
    source_url = fal_client.upload_file(str(source))
    print(f"  Uploading test frame ...")
    target_url = fal_client.upload_file(str(tmp_frame))

    print(f"\n  Calling {ENDPOINT_IMAGE} ...")
    start = time.time()

    def on_update(update):
        if hasattr(update, "logs") and update.logs:
            for log in update.logs:
                msg = log.get("message", "") if isinstance(log, dict) else str(log)
                if msg:
                    print(f"    [fal] {msg}")

    result = fal_client.subscribe(
        ENDPOINT_IMAGE,
        arguments={
            "source_face_url": source_url,
            "target_image_url": target_url,
        },
        with_logs=True,
        on_queue_update=on_update,
    )
    elapsed = time.time() - start
    print(f"  Done in {elapsed:.1f}s")

    img_url = ""
    if isinstance(result, dict):
        img = result.get("image") or {}
        img_url = img.get("url") if isinstance(img, dict) else ""
        if not img_url:
            img_url = result.get("url", "")

    if not img_url:
        print(f"  ERROR: no output URL in response: {result}")
        sys.exit(1)

    download_output(img_url, output)
    print()
    print("  TEST COMPLETE. Check the output image.")
    print("  If the face matches what you want, re-run WITHOUT --test-image-only")
    print("  to process the full video.")


def run_video_swap(fal_client, source: Path, target_video: Path, output: Path):
    print(f"\n  Uploading source photo ({source.stat().st_size // 1024} KB) ...")
    source_url = fal_client.upload_file(str(source))
    print(f"  Source uploaded: {source_url[:80]}...")

    video_size_mb = target_video.stat().st_size / 1024 / 1024
    print(f"  Uploading target video ({video_size_mb:.1f} MB) ... this may take a while")
    target_url = fal_client.upload_file(str(target_video))
    print(f"  Video uploaded: {target_url[:80]}...")

    print(f"\n  Calling {ENDPOINT_VIDEO} ...")
    print(f"  Fal.ai caps: max 25 min video, 25 fps (will truncate/downsample if over)")
    print(f"  Processing starts now. You will see queue updates below.\n")

    start = time.time()

    def on_update(update):
        status = type(update).__name__
        if hasattr(update, "logs") and update.logs:
            for log in update.logs:
                msg = log.get("message", "") if isinstance(log, dict) else str(log)
                if msg:
                    print(f"    [fal] {msg}")
        else:
            elapsed = time.time() - start
            print(f"    [fal] status={status}  elapsed={elapsed:.0f}s")

    result = fal_client.subscribe(
        ENDPOINT_VIDEO,
        arguments={
            "source_face_url": source_url,
            "target_video_url": target_url,
        },
        with_logs=True,
        on_queue_update=on_update,
    )

    elapsed = time.time() - start
    print(f"\n  Fal.ai finished in {elapsed:.0f}s")

    # Response shape: { "video": { "url": "...", "content_type": "video/mp4", ... } }
    video_url = ""
    if isinstance(result, dict):
        vid = result.get("video") or {}
        if isinstance(vid, dict):
            video_url = vid.get("url", "")
        if not video_url:
            video_url = result.get("url", "")

    if not video_url:
        print(f"  ERROR: no output video URL in response")
        print(f"  Raw response: {result}")
        sys.exit(1)

    download_output(video_url, output)


def main():
    parser = argparse.ArgumentParser(
        description="Cloud video face swap via Fal.ai Half-Moon AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_video", help="Path to input video (mp4/mov/mkv/...)")
    parser.add_argument(
        "reference",
        help="Reference photo (single file) OR folder with multiple photos "
             "(script auto-picks the largest)",
    )
    parser.add_argument("--output", "-o", help="Output path (default under output/cloud_video_swap/)")
    parser.add_argument(
        "--test-image-only",
        action="store_true",
        help="Cheap test: extract 1 frame from video, swap as image, download. "
             "Use this to verify identity quality before paying for full video processing.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip the confirmation prompt",
    )

    args = parser.parse_args()

    require_api_key()
    fal_client = require_fal_client()

    input_video = Path(args.input_video)
    if not input_video.exists():
        print(f"  ERROR: video not found: {input_video}")
        sys.exit(1)
    if input_video.suffix.lower() not in VIDEO_EXTS:
        print(f"  WARNING: unusual video extension: {input_video.suffix}")

    source = pick_best_reference(Path(args.reference))

    output = Path(args.output) if args.output else default_output(input_video, args.test_image_only)
    output.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  Fal.ai Cloud Video Face Swap (Half-Moon AI)")
    print("=" * 60)
    print(f"  Source photo : {source}")
    print(f"  Target video : {input_video}")
    print(f"  Output       : {output}")
    print(f"  Mode         : {'TEST (1 image swap, cheap)' if args.test_image_only else 'FULL VIDEO'}")
    print(f"  Endpoint     : {ENDPOINT_IMAGE if args.test_image_only else ENDPOINT_VIDEO}")
    print("=" * 60)
    print()

    if args.test_image_only:
        print("  Cost estimate: a few cents for a single image swap.")
    else:
        video_size_mb = input_video.stat().st_size / 1024 / 1024
        print(f"  Video size: {video_size_mb:.1f} MB")
        print("  Cost estimate: depends on duration. Fal.ai bills per video second of")
        print("  processing. A 1 minute clip is typically well under $1. Check current")
        print("  pricing at https://fal.ai/models/half-moon-ai/ai-face-swap/faceswapvideo")

    if not args.yes:
        print()
        ans = input("  Continue? (y/Enter to proceed, anything else to abort) > ").strip().lower()
        if ans not in ("", "y", "yes"):
            print("  Aborted.")
            sys.exit(0)

    if args.test_image_only:
        run_image_test(fal_client, source, input_video, output)
    else:
        run_video_swap(fal_client, source, input_video, output)

    print()
    print("=" * 60)
    print(f"  DONE  ->  {output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
