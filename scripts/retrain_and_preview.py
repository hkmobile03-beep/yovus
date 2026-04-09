"""
Smart retrain: auto-detect identity -> confirm -> train -> preview

Usage:
  python scripts/retrain_and_preview.py C:/Users/junqi/Desktop/girl
"""
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/retrain_and_preview.py <photos_folder>")
        sys.exit(1)

    photos_dir = Path(sys.argv[1])
    if not photos_dir.exists():
        print(f"ERROR: Folder not found: {photos_dir}")
        sys.exit(1)

    photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = [f for f in photos_dir.iterdir() if f.suffix.lower() in photo_exts]
    print(f"Found {len(photos)} photos in {photos_dir}")

    if not photos:
        print("ERROR: No photos found!")
        sys.exit(1)

    # ══════════════════════════════════════════════════
    # Step 1: Auto-detect person identity
    # ══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  Step 1: Auto-detecting person identity...")
    print("=" * 60)

    from src.pipeline.body_swapper import IdentityAnalyzer

    analyzer = IdentityAnalyzer(device="cuda")
    try:
        features = analyzer.analyze(photos_dir, sample_count=10)
    except Exception as e:
        print(f"  Warning: Auto-detection failed ({e}), using defaults")
        features = {
            "trigger_word": "sks",
            "gender": "female",
            "age_range": "young",
            "age_avg": 25,
            "hair_color": "dark",
            "has_bangs": False,
            "skin_tone": "medium",
            "ethnicity_hint": "",
            "description": "a young woman",
            "folder_name": photos_dir.name,
            "photo_count": len(photos),
        }

    # Display detected features
    print(f"\n  {'─' * 40}")
    print(f"  Detected Identity:")
    print(f"  {'─' * 40}")
    print(f"  Gender:     {features.get('gender', 'unknown')}")
    print(f"  Age:        ~{features.get('age_avg', '?')} ({features.get('age_range', '?')})")
    print(f"  Hair:       {features.get('hair_color', '?')}")
    print(f"  Bangs:      {'Yes' if features.get('has_bangs') else 'No'}")
    print(f"  Skin:       {features.get('skin_tone', '?')}")
    if features.get("ethnicity_hint"):
        print(f"  Ethnicity:  {features.get('ethnicity_hint')}")
    print(f"  {'─' * 40}")
    print(f"  Description: {features.get('description', '?')}")
    print(f"  {'─' * 40}")

    # Generate sample captions
    full_caps, face_caps = analyzer.generate_captions(features)
    print(f"\n  Sample captions that will be used for training:")
    for i, c in enumerate(full_caps[:3]):
        print(f"    [{i+1}] {c}")
    print(f"    ... ({len(full_caps)} full + {len(face_caps)} face captions)")

    # Ask user to confirm
    print(f"\n  Is this correct? (y/n/edit)")
    print(f"  - Press Enter or 'y' to confirm and start training")
    print(f"  - Press 'n' to cancel")
    print(f"  - Type a correction like 'male' or 'blonde hair' to adjust")

    user_input = input("\n  > ").strip().lower()

    if user_input == "n":
        print("Cancelled.")
        sys.exit(0)
    elif user_input and user_input != "y":
        # Apply corrections
        corrections = user_input
        if "male" in corrections and "female" not in corrections:
            features["gender"] = "male"
        if "female" in corrections:
            features["gender"] = "female"
        for color in ["black", "brown", "blonde", "red", "gray", "white"]:
            if color in corrections:
                features["hair_color"] = color
        if "bangs" in corrections:
            features["has_bangs"] = True
        if "no bangs" in corrections:
            features["has_bangs"] = False
        if "old" in corrections or "elderly" in corrections:
            features["age_range"] = "elderly"
        if "young" in corrections:
            features["age_range"] = "young"

        # Rebuild description
        features["description"] = analyzer._build_description(features)
        full_caps, face_caps = analyzer.generate_captions(features)

        print(f"\n  Updated: {features['description']}")
        print(f"  Sample caption: {full_caps[0]}")

    # ══════════════════════════════════════════════════
    # Step 2: Clean old data
    # ══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  Step 2: Cleaning old training data...")
    print("=" * 60)

    dirs_to_clean = [
        PROJECT_ROOT / "models" / "lora",
        PROJECT_ROOT / "temp" / "lora_data",
        PROJECT_ROOT / "output" / "lora_preview",
    ]
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Deleted: {d}")
    print("  Clean!")

    # ══════════════════════════════════════════════════
    # Step 3: Prepare training data with identity-aware captions
    # ══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  Step 3: Preparing training data...")
    print("=" * 60)

    from src.pipeline.body_swapper import LoRATrainer

    trainer = LoRATrainer(device="cuda")
    prep = trainer.prepare_training_data(
        photos_dir,
        PROJECT_ROOT / "temp" / "lora_data",
        target_size=512,
        trigger_word=features["trigger_word"],
        identity_features=features,
        progress_callback=lambda m: print(f"  {m}"),
    )
    print(f"  Prepared: {prep['count']} images ({prep.get('face_crops', 0)} face crops)")

    # ══════════════════════════════════════════════════
    # Step 4: Train LoRA
    # ══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  Step 4: Training LoRA...")
    print("=" * 60)

    lora_output = trainer.train(
        Path(prep["path"]),
        PROJECT_ROOT / "models" / "lora",
        steps=1500,
        rank=16,
        lr=1e-4,
        trigger_word=features["trigger_word"],
        callback=lambda m: print(f"  {m}"),
    )
    print(f"  LoRA saved to: {lora_output}")

    # ══════════════════════════════════════════════════
    # Step 5: Generate preview with identity-specific prompts
    # ══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  Step 5: Generating preview images...")
    print("=" * 60)

    import torch
    from diffusers import StableDiffusionPipeline, UniPCMultistepScheduler

    print("  Loading SD pipeline + LoRA...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
        safety_checker=None,
    )
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)

    print(f"  Loading LoRA from: {lora_output}")
    pipe.load_lora_weights(str(lora_output))
    print("  LoRA loaded!")

    pipe.enable_model_cpu_offload()
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    # Use identity-aware prompts for preview
    tw = features["trigger_word"]
    desc = features["description"]
    prompts = [
        (f"a photo of {tw} person, {desc}, front view, professional portrait, high quality, detailed face, studio lighting", "portrait"),
        (f"a photo of {tw} person, {desc}, full body, standing, professional photography, natural lighting, high quality", "fullbody"),
        (f"a close up photo of {tw} person face, {desc}, detailed, sharp focus, studio portrait, high quality", "closeup"),
    ]
    negative = "low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly, text, watermark, cartoon, anime"

    output_dir = PROJECT_ROOT / "output" / "lora_preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save identity info for reference
    import json
    (output_dir / "identity.json").write_text(
        json.dumps(features, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    generator = torch.Generator(device="cpu").manual_seed(42)

    for prompt, name in prompts:
        print(f"  Generating: {name}...")
        print(f"    Prompt: {prompt[:80]}...")
        image = pipe(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=30,
            guidance_scale=7.5,
            width=512,
            height=768,
            generator=generator,
        ).images[0]

        out_path = output_dir / f"preview_{name}.png"
        image.save(str(out_path))
        print(f"    Saved: {out_path}")

    del pipe
    torch.cuda.empty_cache()

    # ══════════════════════════════════════════════════
    # Done
    # ══════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  COMPLETE!")
    print("=" * 60)
    print(f"\n  Detected identity: {features['description']}")
    print(f"  Preview images:    {output_dir}")
    print(f"    - preview_portrait.png")
    print(f"    - preview_fullbody.png")
    print(f"    - preview_closeup.png")
    print(f"\n  Please open the folder and verify the person matches your photos.")
    print(f"  If correct, run: python main.py")


if __name__ == "__main__":
    main()
