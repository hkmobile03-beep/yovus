"""
Cloud LoRA Training - Train on Fal.ai or Replicate with Flux model
Much better quality than local SD 1.5 (Flux >> SD 1.5 for face identity)

Usage:
  python scripts/cloud_train.py <photos_folder> --provider fal --api-key <KEY>
  python scripts/cloud_train.py <photos_folder> --provider replicate --api-key <KEY>

Pricing:
  Fal.ai:     ~$0.50 per training (~5 min)
  Replicate:  ~$1.50 per training (~15 min)
"""
import sys
import os
import argparse
import logging
import zipfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="  [%(name)s] %(message)s")


def zip_photos(photos_dir: Path) -> Path:
    """Pack photos into a zip for upload"""
    zip_path = photos_dir.parent / f"{photos_dir.name}_training.zip"
    photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    photos = [f for f in photos_dir.iterdir() if f.suffix.lower() in photo_exts]
    print(f"  Packing {len(photos)} photos into zip...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in photos:
            zf.write(f, f.name)

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"  Zip created: {zip_path} ({size_mb:.1f}MB)")
    return zip_path


def train_fal(photos_dir: Path, api_key: str, trigger_word: str, steps: int):
    """Train Flux LoRA on Fal.ai (fastest, cheapest)"""
    try:
        import fal_client
    except ImportError:
        print("  ERROR: pip install fal-client")
        sys.exit(1)

    os.environ["FAL_KEY"] = api_key

    # Zip and upload photos
    zip_path = zip_photos(photos_dir)
    print(f"  Uploading to Fal.ai...")
    zip_url = fal_client.upload_file(str(zip_path))
    print(f"  Upload complete!")

    # Start training
    print(f"\n  Starting Flux LoRA training on Fal.ai...")
    print(f"  Trigger word: {trigger_word}")
    print(f"  Steps: {steps}")
    print(f"  Estimated time: ~5 minutes")
    print(f"  Estimated cost: ~$0.50")
    print(f"  Waiting for completion...\n")

    start = time.time()

    def on_update(update):
        if hasattr(update, 'logs') and update.logs:
            for log in update.logs:
                msg = log.get('message', '') if isinstance(log, dict) else str(log)
                if msg:
                    print(f"  [fal] {msg}")

    result = fal_client.subscribe(
        "fal-ai/flux-lora-fast-training",
        arguments={
            "images_data_url": zip_url,
            "trigger_word": trigger_word,
            "steps": steps,
            "create_masks": True,
            "is_style": False,
        },
        with_logs=True,
        on_queue_update=on_update,
    )

    elapsed = time.time() - start
    lora_url = result.get("diffusers_lora_file", {}).get("url", "")
    config_url = result.get("config_file", {}).get("url", "")

    if lora_url:
        print(f"\n  Training complete! ({elapsed:.0f}s)")
        print(f"  LoRA weights URL: {lora_url}")
        # Download weights
        download_lora(lora_url, config_url)
        return True
    else:
        print(f"  Training failed: {result}")
        return False


def train_replicate(photos_dir: Path, api_key: str, trigger_word: str, steps: int):
    """Train Flux LoRA on Replicate"""
    try:
        import replicate
    except ImportError:
        print("  ERROR: pip install replicate")
        sys.exit(1)

    client = replicate.Client(api_token=api_key)

    zip_path = zip_photos(photos_dir)
    print(f"\n  Starting Flux LoRA training on Replicate...")
    print(f"  Trigger word: {trigger_word}")
    print(f"  Steps: {steps}")
    print(f"  Estimated time: ~15 minutes")
    print(f"  Estimated cost: ~$1.50")
    print(f"  Waiting for completion...\n")

    start = time.time()

    training = client.trainings.create(
        version="ostris/flux-dev-lora-trainer:b6af14222e6bd9be257cbc1ea4afda3cd0503e1133083b9d1de0364d8568e6ef",
        input={
            "input_images": open(str(zip_path), "rb"),
            "trigger_word": trigger_word,
            "steps": steps,
            "learning_rate": 1e-4,
            "batch_size": 1,
            "resolution": "512,768,1024",
            "autocaption": True,
        },
        destination="yovus/face-lora",
    )

    while training.status not in ["succeeded", "failed", "canceled"]:
        time.sleep(15)
        training.reload()
        print(f"  Status: {training.status}...")

    elapsed = time.time() - start

    if training.status == "succeeded":
        print(f"\n  Training complete! ({elapsed:.0f}s)")
        lora_url = str(training.output.get("weights", "")) if isinstance(training.output, dict) else str(training.output)
        print(f"  LoRA URL: {lora_url}")
        download_lora(lora_url)
        return True
    else:
        print(f"  Training failed: {training.error}")
        return False


def download_lora(lora_url: str, config_url: str = ""):
    """Download trained LoRA weights to local models directory"""
    import httpx

    output_dir = PROJECT_ROOT / "models" / "lora" / "lora_weights_cloud"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Downloading LoRA weights...")
    if lora_url:
        resp = httpx.get(lora_url, timeout=120, follow_redirects=True)
        lora_file = output_dir / "pytorch_lora_weights.safetensors"
        lora_file.write_bytes(resp.content)
        print(f"  Saved: {lora_file} ({len(resp.content) / 1024 / 1024:.1f}MB)")

    if config_url:
        resp = httpx.get(config_url, timeout=30, follow_redirects=True)
        config_file = output_dir / "adapter_config.json"
        config_file.write_bytes(resp.content)
        print(f"  Saved: {config_file}")

    print(f"\n  LoRA weights saved to: {output_dir}")
    print(f"  These are Flux LoRA weights (not SD 1.5)")
    print(f"  Use cloud inference to generate images with these weights")


def generate_with_cloud_lora(api_key: str, prompt: str, provider: str = "fal"):
    """Generate images using cloud-trained LoRA (Flux inference in cloud)"""
    lora_dir = PROJECT_ROOT / "models" / "lora" / "lora_weights_cloud"
    lora_file = lora_dir / "pytorch_lora_weights.safetensors"

    if not lora_file.exists():
        print("  ERROR: No cloud LoRA weights found. Train first.")
        return

    if provider == "fal":
        try:
            import fal_client
        except ImportError:
            print("  ERROR: pip install fal-client")
            return

        os.environ["FAL_KEY"] = api_key

        print(f"  Uploading LoRA weights to Fal.ai...")
        lora_url = fal_client.upload_file(str(lora_file))

        output_dir = PROJECT_ROOT / "output" / "cloud_preview"
        output_dir.mkdir(parents=True, exist_ok=True)

        prompts = [
            (f"{prompt}, portrait, professional photo, studio lighting", "cloud_portrait"),
            (f"{prompt}, full body, standing, natural lighting", "cloud_fullbody"),
            (f"close up face of {prompt}, detailed, sharp focus", "cloud_closeup"),
        ]

        for p, name in prompts:
            print(f"  Generating: {name}...")
            result = fal_client.subscribe(
                "fal-ai/flux-lora",
                arguments={
                    "prompt": p,
                    "lora_path": lora_url,
                    "num_images": 1,
                    "image_size": {"width": 768, "height": 1024},
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                },
            )
            img_url = result.get("images", [{}])[0].get("url", "")
            if img_url:
                resp = __import__("httpx").get(img_url, timeout=30, follow_redirects=True)
                out_path = output_dir / f"{name}.png"
                out_path.write_bytes(resp.content)
                print(f"    Saved: {out_path}")

        print(f"\n  Cloud preview images saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Cloud LoRA Training (Flux)")
    parser.add_argument("photos_folder", help="Path to reference photos folder")
    parser.add_argument("--provider", choices=["fal", "replicate"], default="fal",
                        help="Cloud provider (default: fal)")
    parser.add_argument("--api-key", help="API key (or set FAL_KEY / REPLICATE_API_TOKEN env var)")
    parser.add_argument("--trigger-word", default="sks person", help="Trigger word for LoRA")
    parser.add_argument("--steps", type=int, default=1000, help="Training steps (default: 1000)")
    parser.add_argument("--generate", action="store_true", help="Also generate preview images after training")

    args = parser.parse_args()

    photos_dir = Path(args.photos_folder)
    if not photos_dir.exists():
        print(f"ERROR: Folder not found: {photos_dir}")
        sys.exit(1)

    # Get API key
    api_key = args.api_key
    if not api_key:
        if args.provider == "fal":
            api_key = os.environ.get("FAL_KEY", "")
        else:
            api_key = os.environ.get("REPLICATE_API_TOKEN", "")

    if not api_key:
        print(f"\n  {args.provider.upper()} API Key required.")
        if args.provider == "fal":
            print(f"  Get one at: https://fal.ai/dashboard/keys")
        else:
            print(f"  Get one at: https://replicate.com/account/api-tokens")
        api_key = input(f"  API Key> ").strip()
        if not api_key:
            sys.exit(1)

    photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = [f for f in photos_dir.iterdir() if f.suffix.lower() in photo_exts]
    print(f"\n  Photos: {len(photos)} in {photos_dir}")
    print(f"  Provider: {args.provider}")
    print(f"  Trigger: {args.trigger_word}")
    print(f"  Steps: {args.steps}")

    # Gemini analysis for better trigger description
    try:
        from src.pipeline.body_swapper import IdentityAnalyzer
        analyzer = IdentityAnalyzer()
        features = analyzer.analyze_with_gemini(photos_dir)
        if features:
            desc = features.get("description", "")
            print(f"  Gemini identity: {desc}")
    except Exception:
        pass

    print(f"\n  Start cloud training? (y/Enter)")
    if input("  > ").strip().lower() not in ("", "y", "yes"):
        sys.exit(0)

    # Train
    if args.provider == "fal":
        success = train_fal(photos_dir, api_key, args.trigger_word, args.steps)
    else:
        success = train_replicate(photos_dir, api_key, args.trigger_word, args.steps)

    if success and args.generate:
        trigger = args.trigger_word
        desc = "a young Asian woman with dark brown hair and bangs"
        try:
            if features:
                desc = features.get("description", desc)
        except NameError:
            pass
        generate_with_cloud_lora(api_key, f"a photo of {trigger}, {desc}", args.provider)


if __name__ == "__main__":
    main()
