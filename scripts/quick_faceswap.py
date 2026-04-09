"""
Quick face swap: apply reference face to existing generated images.
No need to re-run training or generation.
"""
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    import logging
    logging.basicConfig(level=logging.INFO, format="  [%(name)s] %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python scripts/quick_faceswap.py <reference_photos_folder>")
        sys.exit(1)

    photos_dir = Path(sys.argv[1])
    if not photos_dir.exists():
        print(f"ERROR: Folder not found: {photos_dir}")
        sys.exit(1)

    from src.config.settings import config
    from src.pipeline.body_swapper import apply_face_swap_to_image

    models_dir = config.paths.models_dir
    inswapper = models_dir / "inswapper_128.onnx"
    if not inswapper.exists():
        print(f"ERROR: inswapper_128.onnx not found at {inswapper}")
        print(f"Download: https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx")
        sys.exit(1)

    # Find all generated preview images
    preview_dirs = [
        PROJECT_ROOT / "output" / "lora_preview",
        PROJECT_ROOT / "output" / "style_preview",
    ]

    total = 0
    success = 0

    for preview_dir in preview_dirs:
        if not preview_dir.exists():
            continue

        pngs = sorted(preview_dir.glob("*.png"))
        # Skip already-swapped or backup files
        pngs = [p for p in pngs if "_lora_only" not in p.name and "_faceswap" not in p.name]

        if not pngs:
            continue

        print(f"\n  Processing: {preview_dir.name}/")
        for img_path in pngs:
            total += 1
            # Backup original
            backup = img_path.parent / f"{img_path.stem}_original{img_path.suffix}"
            if not backup.exists():
                shutil.copy2(img_path, backup)

            # Apply face swap
            print(f"    Swapping: {img_path.name}...")
            result = apply_face_swap_to_image(
                generated_image_path=img_path,
                reference_photos_dir=photos_dir,
                models_dir=models_dir,
            )
            if result:
                success += 1
                print(f"    OK: {img_path.name}")
            else:
                # Restore original if swap failed
                shutil.copy2(backup, img_path)
                print(f"    SKIP: {img_path.name} (no face detected)")

    print(f"\n  {'=' * 50}")
    print(f"  Face swap complete: {success}/{total} images")
    print(f"  Originals saved as *_original.png")
    print(f"  Open the folders to compare:")
    for d in preview_dirs:
        if d.exists():
            print(f"    {d}")
    print(f"  {'=' * 50}")


if __name__ == "__main__":
    main()
