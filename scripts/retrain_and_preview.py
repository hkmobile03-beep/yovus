"""
完全リセット → LoRA再学習 → プレビュー生成
一つのコマンドで全部実行

Usage:
  python scripts/retrain_and_preview.py C:/Users/junqi/Desktop/girl
  python scripts/retrain_and_preview.py C:/Users/junqi/Desktop/test
"""
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/retrain_and_preview.py <photos_folder>")
        print("Example: python scripts/retrain_and_preview.py C:\\Users\\junqi\\Desktop\\girl")
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

    # ── Step 1: Clean ALL old data ──
    print("\n" + "=" * 50)
    print("Step 1: Cleaning all old training data and LoRA weights...")
    print("=" * 50)

    dirs_to_clean = [
        PROJECT_ROOT / "models" / "lora",
        PROJECT_ROOT / "temp" / "lora_data",
        PROJECT_ROOT / "output" / "lora_preview",
    ]
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Deleted: {d}")
    print("  Clean complete!")

    # ── Step 2: Prepare training data ──
    print("\n" + "=" * 50)
    print("Step 2: Preparing training data...")
    print("=" * 50)

    from src.pipeline.body_swapper import LoRATrainer

    trainer = LoRATrainer(device="cuda")
    prep = trainer.prepare_training_data(
        photos_dir,
        PROJECT_ROOT / "temp" / "lora_data",
        target_size=512,
        progress_callback=lambda m: print(f"  {m}"),
    )
    print(f"  Prepared: {prep['count']} images ({prep.get('face_crops', 0)} face crops)")

    # ── Step 3: Train LoRA ──
    print("\n" + "=" * 50)
    print("Step 3: Training LoRA (this will take ~15-25 min on RTX 5070)...")
    print("=" * 50)

    lora_output = trainer.train(
        Path(prep["path"]),
        PROJECT_ROOT / "models" / "lora",
        steps=1500,  # will auto-increase if dataset is large
        rank=16,
        lr=1e-4,
        callback=lambda m: print(f"  {m}"),
    )
    print(f"  LoRA saved to: {lora_output}")

    # ── Step 4: Generate preview images ──
    print("\n" + "=" * 50)
    print("Step 4: Generating preview images...")
    print("=" * 50)

    import torch
    from diffusers import StableDiffusionPipeline, UniPCMultistepScheduler

    print("  Loading SD pipeline + LoRA...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
        safety_checker=None,
    )
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)

    # Load LoRA BEFORE cpu_offload
    print(f"  Loading LoRA from: {lora_output}")
    pipe.load_lora_weights(str(lora_output))
    print("  LoRA loaded!")

    pipe.enable_model_cpu_offload()
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    prompts = [
        ("a photo of sks person, front view, professional portrait, high quality, detailed face, studio lighting", "portrait"),
        ("a photo of sks person, full body, standing, professional photography, natural lighting, high quality", "fullbody"),
        ("a close up photo of sks person face, detailed, sharp focus, studio portrait, high quality", "closeup"),
    ]
    negative = "low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly, text, watermark, cartoon, anime"

    output_dir = PROJECT_ROOT / "output" / "lora_preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = torch.Generator(device="cpu").manual_seed(42)

    for prompt, name in prompts:
        print(f"  Generating: {name}...")
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
        print(f"  Saved: {out_path}")

    del pipe
    torch.cuda.empty_cache()

    # ── Done ──
    print("\n" + "=" * 50)
    print("COMPLETE!")
    print("=" * 50)
    print(f"\nPreview images: {output_dir}")
    print(f"  - preview_portrait.png")
    print(f"  - preview_fullbody.png")
    print(f"  - preview_closeup.png")
    print(f"\nPlease open the folder and check if the person matches your reference photos.")
    print(f"If it looks correct, you can proceed with video processing via python main.py")


if __name__ == "__main__":
    main()
