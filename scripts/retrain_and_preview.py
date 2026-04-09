"""
Smart LoRA Training Pipeline - 5-Step Interactive Flow

Step 1: Gemini Vision analysis (detect person features)
Step 2: Style preview (verify description WITHOUT training)
Step 3: Auto-configure LoRA parameters
Step 4: Full LoRA training
Step 5: Identity preview (verify trained result)

Usage:
  python scripts/retrain_and_preview.py C:/Users/junqi/Desktop/test
"""
import sys
import os
import gc
import shutil
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_gemini_key():
    """Load or prompt for Gemini API key"""
    key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    env_file = PROJECT_ROOT / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        print("\n  Gemini API Key required for accurate identity analysis.")
        print("  Get one free: https://aistudio.google.com/apikey")
        key = input("  API Key> ").strip()
        if key:
            with open(env_file, "a", encoding="utf-8") as f:
                f.write(f"\nGEMINI_API_KEY={key}\n")
            print("  Saved to .env")
    return key


def step1_analyze(photos_dir, gemini_key):
    """Step 1: Gemini Vision analysis"""
    print("\n" + "=" * 60)
    print("  STEP 1/5: AI Identity Analysis (Gemini Vision)")
    print("=" * 60)

    from src.pipeline.body_swapper import IdentityAnalyzer

    analyzer = IdentityAnalyzer(device="cuda", gemini_api_key=gemini_key)

    # Try Gemini first
    features = analyzer.analyze_with_gemini(photos_dir, sample_count=5)
    if features:
        print(f"\n  [Gemini Vision] Analysis complete!")
    else:
        print(f"\n  [Gemini unavailable] Using local analysis...")
        features = analyzer.analyze(photos_dir, sample_count=10)

    # Display all detected features
    print(f"\n  {'━' * 50}")
    print(f"  ┃  DETECTED IDENTITY")
    print(f"  {'━' * 50}")
    print(f"  ┃  Gender:      {features.get('gender', '?')}")
    print(f"  ┃  Age:         ~{features.get('age_avg', '?')} ({features.get('age_range', '?')})")
    print(f"  ┃  Hair color:  {features.get('hair_color', '?')}")
    if features.get("hair_style"):
        print(f"  ┃  Hair style:  {features['hair_style']}")
    if features.get("hair_length"):
        print(f"  ┃  Hair length: {features['hair_length']}")
    print(f"  ┃  Bangs:       {'Yes' if features.get('has_bangs') else 'No'}")
    print(f"  ┃  Skin tone:   {features.get('skin_tone', '?')}")
    if features.get("ethnicity_hint"):
        print(f"  ┃  Ethnicity:   {features['ethnicity_hint']}")
    if features.get("face_shape"):
        print(f"  ┃  Face shape:  {features['face_shape']}")
    if features.get("eye_shape"):
        print(f"  ┃  Eye shape:   {features['eye_shape']}")
    if features.get("notable_features"):
        nf = features["notable_features"]
        if isinstance(nf, list):
            nf = ", ".join(nf)
        print(f"  ┃  Features:    {nf}")
    print(f"  {'━' * 50}")
    print(f"  ┃  Description:")
    print(f"  ┃  {features.get('description', '?')}")
    print(f"  {'━' * 50}")

    # Show sample captions
    full_caps, face_caps = analyzer.generate_captions(features)
    print(f"\n  Training captions (sample):")
    for i, c in enumerate(full_caps[:2]):
        print(f"    Full: {c}")
    for i, c in enumerate(face_caps[:1]):
        print(f"    Face: {c}")

    # User confirmation
    print(f"\n  Is this correct?")
    print(f"  [Enter] = Yes  |  [n] = Cancel  |  Type correction (e.g. 'black hair, no bangs')")
    user = input("\n  > ").strip().lower()

    if user == "n":
        print("  Cancelled.")
        sys.exit(0)
    elif user and user != "y" and user != "":
        # Apply corrections
        for color in ["black", "dark brown", "brown", "light brown", "blonde", "red", "gray", "white"]:
            if color in user:
                features["hair_color"] = color
        if "male" in user and "female" not in user:
            features["gender"] = "male"
        if "female" in user:
            features["gender"] = "female"
        if "bangs" in user and "no bangs" not in user:
            features["has_bangs"] = True
        if "no bangs" in user:
            features["has_bangs"] = False
        if "asian" in user:
            features["ethnicity_hint"] = "Asian"
        if "japan" in user:
            features["ethnicity_hint"] = "Japanese"
        if "long" in user:
            features["hair_length"] = "long"
        if "short" in user:
            features["hair_length"] = "short"

        features["description"] = analyzer._build_description(features)
        print(f"\n  Updated: {features['description']}")

    return features, analyzer


def _load_sd_pipeline(model_name=None):
    """Load SD pipeline with Realistic Vision (fallback to vanilla SD 1.5)"""
    import torch
    from diffusers import StableDiffusionPipeline, UniPCMultistepScheduler
    from src.pipeline.body_swapper import REALISTIC_BASE_MODEL, FALLBACK_BASE_MODEL

    base = model_name or REALISTIC_BASE_MODEL
    try:
        print(f"  Loading pipeline: {base}...")
        pipe = StableDiffusionPipeline.from_pretrained(
            base,
            torch_dtype=torch.float16,
            safety_checker=None,
        )
    except Exception as e:
        if base != FALLBACK_BASE_MODEL:
            print(f"  {base} unavailable ({e}), falling back to SD 1.5...")
            pipe = StableDiffusionPipeline.from_pretrained(
                FALLBACK_BASE_MODEL,
                torch_dtype=torch.float16,
                safety_checker=None,
            )
        else:
            raise

    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    return pipe


def step2_style_preview(features, analyzer):
    """Step 2: Generate style preview WITHOUT training (instant verification)"""
    print("\n" + "=" * 60)
    print("  STEP 2/5: Style Preview (no training needed, ~30 seconds)")
    print("=" * 60)

    import torch

    pipe = _load_sd_pipeline()
    pipe.enable_model_cpu_offload()
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    tw = features["trigger_word"]
    desc = features["description"]
    full_caps, face_caps = analyzer.generate_captions(features)

    # Use actual training prompts (but without "sks" since no LoRA yet)
    # Replace trigger word with description for preview
    preview_prompts = [
        (f"a portrait of {desc}, professional photography, studio lighting, high quality, detailed face", "style_portrait"),
        (f"a photo of {desc}, full body, standing, natural lighting, high quality", "style_fullbody"),
        (f"a close up face of {desc}, sharp focus, studio portrait, high quality, detailed", "style_closeup"),
    ]
    negative = "low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly, text, watermark, cartoon, anime"

    output_dir = PROJECT_ROOT / "output" / "style_preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = torch.Generator(device="cpu").manual_seed(42)

    print(f"  Generating style preview based on: {desc}")
    for prompt, name in preview_prompts:
        print(f"  Generating: {name}...")
        image = pipe(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=25,
            guidance_scale=7.5,
            width=512,
            height=768,
            generator=generator,
        ).images[0]

        out_path = output_dir / f"{name}.png"
        image.save(str(out_path))
        print(f"    Saved: {out_path}")

    # Free VRAM
    del pipe
    torch.cuda.empty_cache()
    import gc
    gc.collect()

    print(f"\n  {'━' * 50}")
    print(f"  Style previews saved to: {output_dir}")
    print(f"  {'━' * 50}")
    print(f"  These show the TARGET STYLE based on your description.")
    print(f"  After LoRA training, the FACE will match your photos.")
    print(f"")
    print(f"  Please open the folder and verify:")
    print(f"  - Hair color/style matches?")
    print(f"  - Gender/age correct?")
    print(f"  - Overall style appropriate?")
    print(f"")
    print(f"  [Enter] = Looks good, proceed to training")
    print(f"  [n] = Cancel")
    print(f"  [retry] = Adjust description and regenerate")

    user = input("\n  > ").strip().lower()
    if user == "n":
        print("  Cancelled.")
        sys.exit(0)
    elif user == "retry":
        return False  # Signal to redo step 1+2

    return True


def step3_auto_config(image_count, features):
    """Step 3: Auto-configure LoRA parameters"""
    print("\n" + "=" * 60)
    print("  STEP 3/5: Auto-Configure LoRA Parameters")
    print("=" * 60)

    from src.pipeline.body_swapper import LoRATrainer

    cfg = LoRATrainer.auto_config(image_count)

    print(f"\n  {'━' * 50}")
    print(f"  ┃  AUTO-CONFIGURED PARAMETERS")
    print(f"  {'━' * 50}")
    print(f"  ┃  Training images:  {cfg['image_count']}")
    print(f"  ┃  LoRA Rank:        {cfg['rank']}")
    print(f"  ┃  Learning Rate:    {cfg['lr']}")
    print(f"  ┃  Training Steps:   {cfg['steps']}")
    print(f"  ┃  Alpha:            {cfg['rank']} x {cfg['alpha_multiplier']} = {int(cfg['rank'] * cfg['alpha_multiplier'])}")
    print(f"  ┃  Approx Epochs:    {cfg['epochs_approx']}")
    print(f"  ┃  Est. Time:        {cfg['steps'] * 0.6 / 60:.0f}-{cfg['steps'] * 1.0 / 60:.0f} min")
    print(f"  {'━' * 50}")
    print(f"  ┃  Reason: {cfg['reason']}")
    print(f"  {'━' * 50}")

    print(f"\n  [Enter] = Confirm and start training")
    print(f"  [n] = Cancel")
    user = input("\n  > ").strip().lower()
    if user == "n":
        print("  Cancelled.")
        sys.exit(0)

    return cfg


def step4_train(photos_dir, features, cfg):
    """Step 4: Full LoRA training"""
    print("\n" + "=" * 60)
    print("  STEP 4/5: LoRA Training")
    print("=" * 60)

    from src.pipeline.body_swapper import LoRATrainer

    # Clean old data
    dirs_to_clean = [
        PROJECT_ROOT / "models" / "lora",
        PROJECT_ROOT / "temp" / "lora_data",
        PROJECT_ROOT / "output" / "lora_preview",
    ]
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Cleaned: {d}")

    trainer = LoRATrainer(device="cuda")

    # Prepare data with identity-aware captions
    print(f"\n  Preparing training data...")
    prep = trainer.prepare_training_data(
        photos_dir,
        PROJECT_ROOT / "temp" / "lora_data",
        target_size=512,
        trigger_word=features["trigger_word"],
        identity_features=features,
        progress_callback=lambda m: print(f"  {m}"),
    )
    print(f"  Data ready: {prep['count']} images ({prep.get('face_crops', 0)} face crops)")

    # Train with auto-configured parameters
    print(f"\n  Starting training (rank={cfg['rank']}, steps={cfg['steps']}, lr={cfg['lr']})...")
    lora_output = trainer.train(
        Path(prep["path"]),
        PROJECT_ROOT / "models" / "lora",
        steps=cfg["steps"],
        rank=cfg["rank"],
        lr=cfg["lr"],
        trigger_word=features["trigger_word"],
        callback=lambda m: print(f"  {m}"),
    )
    print(f"\n  LoRA saved: {lora_output}")
    return lora_output


def step5_verify(features, lora_output, analyzer, photos_dir=None):
    """Step 5: Generate identity preview with trained LoRA + face swap"""
    print("\n" + "=" * 60)
    print("  STEP 5/5: Identity Verification Preview")
    print("=" * 60)

    import torch

    pipe = _load_sd_pipeline()

    # Load LoRA BEFORE cpu_offload
    print(f"  Loading LoRA from: {lora_output}")
    pipe.load_lora_weights(str(lora_output))
    print("  LoRA loaded!")

    pipe.enable_model_cpu_offload()
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    tw = features["trigger_word"]
    desc = features["description"]
    full_caps, face_caps = analyzer.generate_captions(features)

    # Use identity-specific prompts with trigger word
    prompts = [
        (full_caps[0] if full_caps else f"a photo of {tw} person, {desc}, high quality", "identity_portrait"),
        (full_caps[1] if len(full_caps) > 1 else f"a photo of {tw} person, {desc}, full body", "identity_fullbody"),
        (face_caps[0] if face_caps else f"a close up of {tw} person face, {desc}", "identity_closeup"),
    ]
    negative = "low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly, text, watermark, cartoon, anime"

    output_dir = PROJECT_ROOT / "output" / "lora_preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save identity info
    (output_dir / "identity.json").write_text(
        json.dumps(features, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    generator = torch.Generator(device="cpu").manual_seed(42)
    generated_paths = []

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

        out_path = output_dir / f"{name}.png"
        image.save(str(out_path))
        generated_paths.append(out_path)
        print(f"    Saved: {out_path}")

    # Free SD pipeline VRAM before face swap
    del pipe
    torch.cuda.empty_cache()
    gc.collect()

    # ── Face swap post-processing: overlay reference face for exact match ──
    if photos_dir:
        print(f"\n  Applying face swap for exact identity match...")
        from src.pipeline.body_swapper import apply_face_swap_to_image
        from src.config.settings import config

        models_dir = config.paths.models_dir
        swapped_count = 0
        for gen_path in generated_paths:
            # Save original LoRA-only version
            lora_only = gen_path.parent / f"{gen_path.stem}_lora_only{gen_path.suffix}"
            shutil.copy2(gen_path, lora_only)

            result = apply_face_swap_to_image(
                generated_image_path=gen_path,
                reference_photos_dir=photos_dir,
                models_dir=models_dir,
            )
            if result:
                swapped_count += 1
                print(f"    Face swapped: {gen_path.name}")
            else:
                print(f"    Face swap skipped: {gen_path.name} (no face detected)")

        if swapped_count > 0:
            print(f"  Face swap applied to {swapped_count}/{len(generated_paths)} images")
            print(f"  LoRA-only versions saved as *_lora_only.png")
        else:
            print(f"  Face swap not available (inswapper_128.onnx may be missing)")
            print(f"  Download: https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx")
            print(f"  Save to: {models_dir}/inswapper_128.onnx")

    print(f"\n  {'━' * 50}")
    print(f"  ┃  TRAINING COMPLETE!")
    print(f"  {'━' * 50}")
    print(f"  ┃  Identity:  {desc}")
    print(f"  ┃")
    print(f"  ┃  Style preview:    output/style_preview/")
    print(f"  ┃  Identity preview: output/lora_preview/")
    print(f"  ┃  (LoRA-only:       *_lora_only.png)")
    print(f"  ┃  (LoRA+FaceSwap:   identity_*.png)")
    print(f"  ┃")
    print(f"  ┃  The face-swapped images should match your")
    print(f"  ┃  reference photos exactly.")
    print(f"  ┃")
    print(f"  ┃  Ready for video: python main.py")
    print(f"  {'━' * 50}")


def main():
    import logging
    logging.basicConfig(level=logging.INFO, format="  [%(name)s] %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python scripts/retrain_and_preview.py <photos_folder>")
        sys.exit(1)

    photos_dir = Path(sys.argv[1])
    if not photos_dir.exists():
        print(f"ERROR: Folder not found: {photos_dir}")
        sys.exit(1)

    photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    photos = [f for f in photos_dir.iterdir() if f.suffix.lower() in photo_exts]

    if not photos:
        print("ERROR: No photos found!")
        sys.exit(1)

    print(f"\n  Photos folder: {photos_dir}")
    print(f"  Found: {len(photos)} photos")

    # Get Gemini API key
    gemini_key = get_gemini_key()

    # Step 1: Analyze identity
    while True:
        features, analyzer = step1_analyze(photos_dir, gemini_key)

        # Step 2: Style preview (no training)
        approved = step2_style_preview(features, analyzer)
        if approved:
            break
        # If retry, loop back to step 1
        print("\n  Returning to identity analysis...")

    # Step 3: Auto-configure parameters
    cfg = step3_auto_config(len(photos), features)

    # Step 4: Train
    lora_output = step4_train(photos_dir, features, cfg)

    # Step 5: Verify (with face swap post-processing)
    step5_verify(features, lora_output, analyzer, photos_dir=photos_dir)


if __name__ == "__main__":
    main()
