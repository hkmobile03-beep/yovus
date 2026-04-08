"""
LoRA训练效果预览 - 生成单张图片验证数字人身份
无需跑整个视频流程，几秒出图
"""
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def preview():
    import torch
    from diffusers import StableDiffusionPipeline, UniPCMultistepScheduler
    from PIL import Image

    lora_path = PROJECT_ROOT / "models" / "lora" / "lora_weights"

    if not lora_path.exists():
        print("ERROR: LoRA weights directory not found. Please train first.")
        return

    has_weights = (
        any(lora_path.glob("*.safetensors"))
        or any(lora_path.glob("*.bin"))
        or (lora_path / "adapter_config.json").exists()
    )
    if not has_weights:
        print("ERROR: LoRA weights not found. Please train first.")
        return

    print(f"LoRA weights: {lora_path}")
    print("Loading Stable Diffusion pipeline...")

    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
        safety_checker=None,
    )

    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)

    # Load LoRA BEFORE cpu_offload
    print("Loading LoRA weights...")
    pipe.load_lora_weights(str(lora_path))
    print("LoRA loaded!")

    # Enable VRAM optimization
    pipe.enable_model_cpu_offload()
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    # Generate preview images with different prompts
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
        print(f"\nGenerating: {name}...")
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
        print(f"Saved: {out_path}")

    print(f"\n{'='*50}")
    print(f"Preview images saved to: {output_dir}")
    print(f"Please open the folder and check if the person")
    print(f"looks like your reference photos.")
    print(f"{'='*50}")


if __name__ == "__main__":
    preview()
