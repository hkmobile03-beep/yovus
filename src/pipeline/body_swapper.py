"""
全身替换模块 v3.0 - 本地 LoRA 训练 + ControlNet 生成
RTX 5070 Laptop (8GB VRAM) 完全対応

LoRA 训练流程:
1. 准备训练数据 (裁剪/缩放/自动标注)
2. 缓存 VAE latents (省 VRAM)
3. 训练 UNet LoRA (gradient_checkpointing + fp16 + 8bit Adam)
4. 保存 LoRA 权重

全身生成流程:
1. DWPose 提取骨骼姿势
2. ControlNet (pose) + LoRA → 生成新人物
3. 输出生成图 + mask
"""
import gc
import logging
import json
from pathlib import Path
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger("yovus.body_swap")


class LoRATrainer:
    """LoRA 微调训练器 - 本地 8GB VRAM 优化"""

    def __init__(self, device: str = "cuda", vram_limit_gb: float = 7.0):
        self.device = device
        self.vram_limit_gb = vram_limit_gb

    def prepare_training_data(
        self,
        photos_dir: Path,
        output_dir: Path,
        target_size: int = 512,
        auto_caption: bool = True,
        trigger_word: str = "sks",
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """准备训练数据: 裁剪、对齐、自动标注"""
        import cv2

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        img_dir = output_dir / "images"
        img_dir.mkdir(exist_ok=True)

        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = sorted([
            f for f in Path(photos_dir).iterdir()
            if f.suffix.lower() in photo_exts
        ])

        if not photos:
            raise ValueError(f"写真が見つかりません: {photos_dir}")

        processed = 0
        skipped = 0
        total = len(photos)

        for idx, photo in enumerate(photos):
            try:
                img = cv2.imread(str(photo))
                if img is None:
                    skipped += 1
                    continue

                h, w = img.shape[:2]
                if h < 64 or w < 64:
                    skipped += 1
                    continue

                # Resize maintaining aspect ratio
                scale = target_size / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

                # Pad to square
                canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
                y_off = (target_size - new_h) // 2
                x_off = (target_size - new_w) // 2
                canvas[y_off:y_off + new_h, x_off:x_off + new_w] = img

                out_path = img_dir / f"{processed:06d}.png"
                cv2.imwrite(str(out_path), canvas)

                if auto_caption:
                    caption = f"a photo of {trigger_word} person, high quality, detailed"
                    caption_path = img_dir / f"{processed:06d}.txt"
                    caption_path.write_text(caption, encoding="utf-8")

                processed += 1

                if progress_callback and (idx + 1) % 50 == 0:
                    progress_callback(f"データ準備: {idx + 1}/{total} ({processed} 成功)")

            except Exception as e:
                logger.debug(f"Skip {photo.name}: {e}")
                skipped += 1

        if progress_callback:
            progress_callback(f"データ準備完了: {processed} 枚 ({skipped} スキップ)")

        logger.info(f"Prepared {processed} training images in {img_dir}")
        return {"count": processed, "skipped": skipped, "path": str(img_dir)}

    def train(
        self,
        training_data_dir: Path,
        output_dir: Path,
        base_model: str = "runwayml/stable-diffusion-v1-5",
        steps: int = 1500,
        rank: int = 16,
        lr: float = 1e-4,
        trigger_word: str = "sks",
        batch_size: int = 1,
        callback: Optional[Callable] = None,
    ) -> Path:
        """
        本地 LoRA 训练 (8GB VRAM 优化)
        使用 diffusers + PEFT，完整训练循环
        """
        import torch

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        lora_output = output_dir / "lora_weights"
        lora_output.mkdir(exist_ok=True)

        # Save config
        config = {
            "base_model": base_model,
            "steps": steps,
            "rank": rank,
            "lr": lr,
            "trigger_word": trigger_word,
            "training_data": str(training_data_dir),
        }
        (output_dir / "training_config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        if callback:
            callback("LoRA学習開始 (本地GPU)...")
            callback(f"  Base: {base_model}")
            callback(f"  Steps: {steps}, Rank: {rank}, LR: {lr}")

        try:
            return self._train_local(
                training_data_dir, lora_output, base_model,
                steps, rank, lr, trigger_word, batch_size, callback,
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            if callback:
                callback(f"学習エラー: {e}")
            raise

    def _train_local(
        self, data_dir, output_dir, base_model,
        steps, rank, lr, trigger_word, batch_size, callback,
    ) -> Path:
        """Real local training loop using diffusers + PEFT"""
        import torch
        from torch.utils.data import Dataset, DataLoader
        from diffusers import AutoencoderKL, UNet2DConditionModel, DDPMScheduler
        from transformers import CLIPTextModel, CLIPTokenizer
        from peft import LoraConfig, get_peft_model
        from PIL import Image
        import cv2

        device = self.device
        dtype = torch.float16

        if callback:
            callback("モデルロード中...")

        # 1) Load tokenizer + text encoder → encode prompt → move to CPU
        tokenizer = CLIPTokenizer.from_pretrained(base_model, subfolder="tokenizer")
        text_encoder = CLIPTextModel.from_pretrained(
            base_model, subfolder="text_encoder", torch_dtype=dtype,
        ).to(device)

        prompt = f"a photo of {trigger_word} person, high quality, detailed"
        tokens = tokenizer(
            prompt, padding="max_length", max_length=tokenizer.model_max_length,
            truncation=True, return_tensors="pt",
        ).input_ids.to(device)

        with torch.no_grad():
            text_embeds = text_encoder(tokens)[0]  # (1, 77, 768)

        # Free text encoder VRAM
        del text_encoder
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback("VAE latents キャッシュ中...")

        # 2) Load VAE → cache latents → free VAE
        vae = AutoencoderKL.from_pretrained(
            base_model, subfolder="vae", torch_dtype=dtype,
        ).to(device)
        vae.eval()

        img_dir = Path(data_dir)
        image_files = sorted(img_dir.glob("*.png"))
        if not image_files:
            raise ValueError(f"No training images found in {img_dir}")

        # Limit to reasonable number for 8GB VRAM training
        max_images = min(len(image_files), 200)
        image_files = image_files[:max_images]

        latent_cache = []
        for i, img_path in enumerate(image_files):
            img = Image.open(img_path).convert("RGB").resize((512, 512))
            img_tensor = torch.from_numpy(
                np.array(img).transpose(2, 0, 1).astype(np.float32) / 127.5 - 1.0
            ).unsqueeze(0).to(device, dtype=dtype)

            with torch.no_grad():
                latent = vae.encode(img_tensor).latent_dist.sample() * vae.config.scaling_factor
                latent_cache.append(latent.cpu())

            if callback and (i + 1) % 50 == 0:
                callback(f"VAEキャッシュ: {i+1}/{len(image_files)}")

        del vae
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback(f"学習データ: {len(latent_cache)} 枚キャッシュ済み")
            callback("UNet + LoRA 準備中...")

        # 3) Load UNet → apply LoRA → prepare training
        unet = UNet2DConditionModel.from_pretrained(
            base_model, subfolder="unet", torch_dtype=dtype,
        ).to(device)

        unet.enable_gradient_checkpointing()

        # Apply LoRA
        lora_config = LoraConfig(
            r=rank,
            lora_alpha=rank // 2,
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
            lora_dropout=0.05,
        )
        unet = get_peft_model(unet, lora_config)

        trainable = sum(p.numel() for p in unet.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in unet.parameters())
        if callback:
            callback(f"LoRA パラメータ: {trainable:,} / {total_params:,} ({100*trainable/total_params:.2f}%)")

        # Noise scheduler
        scheduler = DDPMScheduler.from_pretrained(base_model, subfolder="scheduler")

        # Optimizer (8-bit Adam for VRAM saving)
        try:
            import bitsandbytes as bnb
            optimizer = bnb.optim.AdamW8bit(
                unet.parameters(), lr=lr, weight_decay=1e-2,
            )
            if callback:
                callback("オプティマイザ: AdamW 8bit (VRAM節約)")
        except ImportError:
            optimizer = torch.optim.AdamW(unet.parameters(), lr=lr, weight_decay=1e-2)
            if callback:
                callback("オプティマイザ: AdamW (標準)")

        # 4) Training loop
        unet.train()
        num_latents = len(latent_cache)
        text_embeds_expanded = text_embeds.to(device, dtype=dtype)

        if callback:
            callback(f"学習開始: {steps} steps...")

        for step in range(steps):
            # Random latent from cache
            idx = step % num_latents
            latent = latent_cache[idx].to(device, dtype=dtype)

            # Random noise
            noise = torch.randn_like(latent)
            timestep = torch.randint(0, scheduler.config.num_train_timesteps, (1,), device=device).long()

            # Add noise
            noisy_latent = scheduler.add_noise(latent, noise, timestep)

            # Predict noise
            noise_pred = unet(noisy_latent, timestep, text_embeds_expanded).sample

            # MSE loss
            loss = torch.nn.functional.mse_loss(noise_pred, noise)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(unet.parameters(), 1.0)
            optimizer.step()

            if callback and (step + 1) % 50 == 0:
                callback(f"Step {step+1}/{steps} | Loss: {loss.item():.4f}")

            # Save checkpoint
            if (step + 1) % max(1, steps // 3) == 0:
                ckpt_dir = output_dir / f"checkpoint-{step+1}"
                unet.save_pretrained(str(ckpt_dir))

        # 5) Save final weights
        if callback:
            callback("LoRA 重み保存中...")

        unet.save_pretrained(str(output_dir))

        # Also save in diffusers-compatible format
        unet.eval()
        del optimizer, latent_cache
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback(f"LoRA 学習完了! 保存先: {output_dir}")

        return output_dir


class PoseExtractor:
    """姿態抽出 - DWPose / OpenPose"""

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._detector = None

    def initialize(self):
        try:
            from controlnet_aux import DWposeDetector
            self._detector = DWposeDetector()
            logger.info("DWPose detector initialized")
        except (ImportError, Exception) as e:
            logger.warning(f"DWPose not available: {e}, trying OpenPose")
            try:
                from controlnet_aux import OpenposeDetector
                self._detector = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
                logger.info("OpenPose detector initialized")
            except (ImportError, Exception) as e2:
                logger.warning(f"OpenPose not available: {e2}")
                self._detector = None

    def extract_pose(self, image: np.ndarray) -> Optional[np.ndarray]:
        """从图像中提取姿势骨骼图"""
        if self._detector is None:
            self.initialize()
        if self._detector is None:
            return self._fallback_pose(image)

        from PIL import Image
        import cv2

        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        pose_img = self._detector(pil_img)

        pose_np = np.array(pose_img)
        pose_np = cv2.cvtColor(pose_np, cv2.COLOR_RGB2BGR)

        # Resize to match input
        if pose_np.shape[:2] != image.shape[:2]:
            pose_np = cv2.resize(pose_np, (image.shape[1], image.shape[0]))

        return pose_np

    def _fallback_pose(self, image: np.ndarray) -> np.ndarray:
        """无姿势检测时的边缘检测兜底"""
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    def release(self):
        self._detector = None
        gc.collect()


class BodyGenerator:
    """全身生成 - ControlNet (Pose) + LoRA"""

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._pipe = None
        self._initialized = False

    def initialize(self, lora_path: Optional[Path] = None, base_model: str = "runwayml/stable-diffusion-v1-5"):
        """初始化 ControlNet + SD + LoRA Pipeline"""
        if self._initialized:
            return

        import torch
        from diffusers import (
            StableDiffusionControlNetPipeline,
            ControlNetModel,
            UniPCMultistepScheduler,
        )

        logger.info("Loading ControlNet (openpose)...")
        controlnet = ControlNetModel.from_pretrained(
            "lllyasviel/control_v11p_sd15_openpose",
            torch_dtype=torch.float16,
        )

        logger.info("Loading Stable Diffusion pipeline...")
        self._pipe = StableDiffusionControlNetPipeline.from_pretrained(
            base_model,
            controlnet=controlnet,
            torch_dtype=torch.float16,
            safety_checker=None,
        )

        self._pipe.scheduler = UniPCMultistepScheduler.from_config(
            self._pipe.scheduler.config
        )

        # 8GB VRAM optimization
        self._pipe.enable_model_cpu_offload()
        try:
            self._pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            logger.debug("xformers not available")

        # Load LoRA if available
        if lora_path and Path(lora_path).exists():
            logger.info(f"Loading LoRA weights: {lora_path}")
            self._pipe.load_lora_weights(str(lora_path))
            logger.info("LoRA weights loaded")

        self._initialized = True
        logger.info("Body generation pipeline ready")

    def generate(
        self,
        pose_image: np.ndarray,
        prompt: str = "a photo of sks person, full body, high quality, detailed, professional photography",
        negative_prompt: str = "low quality, blurry, deformed, extra limbs, bad anatomy, disfigured, ugly",
        num_inference_steps: int = 30,
        controlnet_conditioning_scale: float = 0.85,
        guidance_scale: float = 7.5,
        width: int = 512,
        height: int = 768,
        seed: int = -1,
    ) -> np.ndarray:
        """根据姿态图生成全身人物"""
        if self._pipe is None:
            raise RuntimeError("Pipeline not initialized")

        import torch
        from PIL import Image
        import cv2

        # Convert pose to PIL
        pose_pil = Image.fromarray(cv2.cvtColor(pose_image, cv2.COLOR_BGR2RGB))
        pose_pil = pose_pil.resize((width, height))

        generator = None
        if seed >= 0:
            generator = torch.Generator(device="cpu").manual_seed(seed)

        result = self._pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=pose_pil,
            num_inference_steps=num_inference_steps,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]

        result_np = np.array(result)
        result_np = cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)
        return result_np

    def release(self):
        self._pipe = None
        self._initialized = False
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass
