"""
Cloud video face swap via Fal.ai.

Replaces faces in a video with the face from a reference photo. Default
endpoint is fal-ai/pixverse/swap, which is officially maintained by fal.ai
and works reliably.

Auth:
  The script looks for FAL_KEY in this order:
    1. FAL_KEY environment variable
    2. .env file at the project root (key=value lines, gitignored)
  Never hardcode the key in tracked source.

Usage:
  python scripts/cloud_video_swap.py <input_video> <reference_photo_or_folder>
  python scripts/cloud_video_swap.py in.mp4 C:\\Users\\junqi\\Desktop\\test
  python scripts/cloud_video_swap.py in.mp4 ref.jpg --output out.mp4
  python scripts/cloud_video_swap.py in.mp4 ref.jpg --endpoint half-moon   # alternate, may 404
  python scripts/cloud_video_swap.py in.mp4 ref.jpg -y                     # skip confirm

Notes:
  - fal-ai/pixverse/swap bills roughly $0.15-$0.40 per 5-second clip
  - Source photo formats: jpg/jpeg/png/webp
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


# Endpoint presets. Each entry defines the fal.ai application name and how to
# map our (source_photo, target_video) pair onto its input JSON.
ENDPOINTS = {
    "pixverse": {
        "app": "fal-ai/pixverse/swap",
        "photo_key": "image_url",
        "video_key": "video_url",
        "description": "fal-ai/pixverse/swap (official, stable, ~$0.15-0.40 / 5s)",
    },
    "half-moon": {
        "app": "half-moon-ai/ai-face-swap/faceswapvideo",
        "photo_key": "source_face_url",
        "video_key": "target_video_url",
        "description": "half-moon-ai/ai-face-swap/faceswapvideo (cheaper but may 404 on some accounts)",
    },
}


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


def default_output(input_path: Path) -> Path:
    out_dir = PROJECT_ROOT / "output" / "cloud_video_swap"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = input_path.suffix or ".mp4"
    return out_dir / f"{input_path.stem}_swapped{suffix}"


def load_dotenv_into_environ():
    """Minimal .env loader. Reads PROJECT_ROOT/.env and populates os.environ
    for any keys that are not already set. No dependency on python-dotenv."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as e:
        print(f"  WARNING: failed to parse .env: {e}")


def require_fal_client():
    try:
        import fal_client  # noqa: F401
        return fal_client
    except ImportError:
        print("  ERROR: fal_client not installed")
        print("  Run: pip install fal-client")
        sys.exit(1)


def require_api_key():
    load_dotenv_into_environ()
    key = os.environ.get("FAL_KEY", "").strip()
    if not key:
        print("  ERROR: FAL_KEY not found")
        print()
        print("  Provide it via either:")
        print("    1. A .env file at project root containing:")
        print("         FAL_KEY=your_key")
        print("    2. PowerShell:  $env:FAL_KEY = \"your_key\"")
        print()
        print("  Get your key at: https://fal.ai/dashboard/keys")
        sys.exit(1)
    return key


def download_output(url: str, output_path: Path):
    import httpx
    print(f"  Downloading result: {url[:80]}...")
    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  Saved: {output_path} ({size_mb:.1f} MB)")


def extract_video_url(result):
    """Pull the output video URL from whatever JSON shape fal returns."""
    if not isinstance(result, dict):
        return ""
    # Common shapes:
    #   {"video": {"url": "..."}}
    #   {"video_url": "..."}
    #   {"output": {"url": "..."}}
    #   {"url": "..."}
    vid = result.get("video")
    if isinstance(vid, dict) and vid.get("url"):
        return vid["url"]
    if isinstance(vid, str):
        return vid
    for key in ("video_url", "output_url", "url"):
        if isinstance(result.get(key), str):
            return result[key]
    out = result.get("output")
    if isinstance(out, dict) and out.get("url"):
        return out["url"]
    return ""


def run_video_swap(fal_client, endpoint: dict, source: Path, target_video: Path, output: Path):
    app = endpoint["app"]
    photo_key = endpoint["photo_key"]
    video_key = endpoint["video_key"]

    print(f"\n  Uploading source photo ({source.stat().st_size // 1024} KB) ...")
    source_url = fal_client.upload_file(str(source))
    print(f"  Source uploaded.")

    video_size_mb = target_video.stat().st_size / 1024 / 1024
    print(f"  Uploading target video ({video_size_mb:.1f} MB) ... this may take a while")
    target_url = fal_client.upload_file(str(target_video))
    print(f"  Video uploaded.")

    print(f"\n  Calling {app} ...")
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

    try:
        result = fal_client.subscribe(
            app,
            arguments={
                photo_key: source_url,
                video_key: target_url,
            },
            with_logs=True,
            on_queue_update=on_update,
        )
    except Exception as e:
        msg = str(e)
        print(f"\n  ERROR calling {app}: {msg}")
        if "not found" in msg.lower() or "404" in msg:
            print()
            print("  The endpoint returned 404. Try a different preset:")
            for name, ep in ENDPOINTS.items():
                if ep["app"] != app:
                    print(f"    --endpoint {name}   -> {ep['description']}")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\n  Fal.ai finished in {elapsed:.0f}s")

    video_url = extract_video_url(result)
    if not video_url:
        print(f"  ERROR: no output video URL in response")
        print(f"  Raw response: {result}")
        sys.exit(1)

    download_output(video_url, output)


def main():
    parser = argparse.ArgumentParser(
        description="Cloud video face swap via Fal.ai",
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
        "--endpoint",
        choices=list(ENDPOINTS.keys()),
        default="pixverse",
        help="Which fal.ai face swap endpoint preset to use (default: pixverse)",
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

    endpoint = ENDPOINTS[args.endpoint]

    input_video = Path(args.input_video)
    if not input_video.exists():
        print(f"  ERROR: video not found: {input_video}")
        sys.exit(1)
    if input_video.suffix.lower() not in VIDEO_EXTS:
        print(f"  WARNING: unusual video extension: {input_video.suffix}")

    source = pick_best_reference(Path(args.reference))
    output = Path(args.output) if args.output else default_output(input_video)
    output.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  Fal.ai Cloud Video Face Swap")
    print("=" * 60)
    print(f"  Source photo : {source}")
    print(f"  Target video : {input_video}")
    print(f"  Output       : {output}")
    print(f"  Endpoint     : {endpoint['app']}")
    print(f"                 {endpoint['description']}")
    print("=" * 60)
    print()

    video_size_mb = input_video.stat().st_size / 1024 / 1024
    print(f"  Video size: {video_size_mb:.1f} MB")
    print("  Cost estimate: varies by endpoint and video duration. pixverse/swap")
    print("  is ~$0.15-0.40 per 5-second clip. A 30-second clip ~ $1-2.50.")

    if not args.yes:
        print()
        ans = input("  Continue? (y/Enter to proceed, anything else to abort) > ").strip().lower()
        if ans not in ("", "y", "yes"):
            print("  Aborted.")
            sys.exit(0)

    run_video_swap(fal_client, endpoint, source, input_video, output)

    print()
    print("=" * 60)
    print(f"  DONE  ->  {output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
