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


class IdentityAnalyzer:
    """自动分析参照照片中的人物特征，生成精准提示词

    Analysis methods (in priority order):
    1. Gemini API (best quality - cloud vision model)
    2. InsightFace + OpenCV (local fallback)
    """

    def __init__(self, device: str = "cuda", gemini_api_key: str = ""):
        self.device = device
        self.gemini_api_key = gemini_api_key or self._load_gemini_key()

    def _load_gemini_key(self) -> str:
        """Try to load Gemini API key from environment or config"""
        import os
        # Check environment variables
        for key_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            val = os.environ.get(key_name, "")
            if val:
                return val
        # Check .env file in project root
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""

    def analyze_with_gemini(self, photos_dir: Path, sample_count: int = 5) -> Optional[dict]:
        """Use Gemini Vision API to analyze person identity from photos.

        Returns structured identity features or None if API unavailable.
        """
        if not self.gemini_api_key:
            logger.info("Gemini API key not found, skipping vision analysis")
            return None

        import base64
        import cv2

        photos_dir = Path(photos_dir)
        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = sorted([f for f in photos_dir.iterdir() if f.suffix.lower() in photo_exts])
        if not photos:
            return None

        # Select diverse samples
        step = max(1, len(photos) // sample_count)
        samples = photos[::step][:sample_count]

        # Encode images to base64 (resize to save bandwidth)
        image_parts = []
        for photo_path in samples[:3]:  # Send 3 photos max to API
            img = cv2.imread(str(photo_path))
            if img is None:
                continue
            # Resize for API efficiency
            h, w = img.shape[:2]
            max_dim = 512
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64 = base64.b64encode(buf).decode("utf-8")
            image_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64,
                }
            })

        if not image_parts:
            return None

        # Build Gemini API request
        prompt_text = (
            "Analyze this person's physical appearance for AI training captions. "
            "Return ONLY a JSON object with these exact fields:\n"
            "{\n"
            '  "gender": "female" or "male",\n'
            '  "age_range": "young" (18-30) or "middle-aged" (30-50) or "elderly" (50+),\n'
            '  "age_estimate": number,\n'
            '  "ethnicity": "Asian" or "European" or "African" or "Latin" or "Middle Eastern" or "mixed",\n'
            '  "hair_color": specific color like "black", "dark brown", "chestnut", "blonde", etc.,\n'
            '  "hair_length": "short", "medium", or "long",\n'
            '  "hair_style": brief description like "straight with bangs", "wavy", "ponytail", etc.,\n'
            '  "has_bangs": true or false,\n'
            '  "skin_tone": "fair", "light", "medium", "tan", or "dark",\n'
            '  "face_shape": "oval", "round", "square", "heart", etc.,\n'
            '  "eye_shape": "almond", "round", "monolid", etc.,\n'
            '  "notable_features": brief list of distinctive features,\n'
            '  "description_en": one sentence describing this person in English for AI image generation\n'
            "}\n"
            "Be precise and objective. The description should help an AI model "
            "learn to generate images of this specific person."
        )

        # Build request parts: images + text prompt
        parts = image_parts + [{"text": prompt_text}]

        try:
            import httpx

            # Vision-capable models only (lite models don't support images)
            model_candidates = [
                "gemini-1.5-flash",
                "gemini-1.5-flash-latest",
                "gemini-2.0-flash",
                "gemini-1.5-pro",
                "gemini-pro-vision",
            ]

            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                }
            }

            logger.info("Calling Gemini Vision API for identity analysis...")
            resp = None
            used_model = None
            for model_name in model_candidates:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={self.gemini_api_key}"
                )
                try:
                    resp = httpx.post(url, json=payload, timeout=60.0)
                    if resp.status_code == 200:
                        used_model = model_name
                        break
                    else:
                        error_detail = ""
                        try:
                            error_detail = resp.json().get("error", {}).get("message", "")
                        except Exception:
                            error_detail = resp.text[:200]
                        logger.debug(f"Model {model_name}: HTTP {resp.status_code} - {error_detail}")
                        continue
                except Exception as req_err:
                    logger.debug(f"Model {model_name}: request error - {req_err}")
                    continue

            if resp is None or resp.status_code != 200:
                logger.warning("All Gemini models failed. Using local analysis.")
                return None

            logger.info(f"Using Gemini model: {used_model}")
            data = resp.json()

            # Extract text response
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.info(f"Gemini response: {text[:200]}...")

            # Parse JSON from response (handle markdown code blocks)
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if not json_match:
                logger.warning("Could not parse JSON from Gemini response")
                return None

            import json as json_mod
            gemini_data = json_mod.loads(json_match.group())

            # Convert Gemini output to our standard features format
            features = {
                "trigger_word": "sks",
                "folder_name": photos_dir.name,
                "photo_count": len(photos),
                "gender": gemini_data.get("gender", "female"),
                "age_range": gemini_data.get("age_range", "young"),
                "age_avg": gemini_data.get("age_estimate", 25),
                "hair_color": gemini_data.get("hair_color", "dark"),
                "hair_length": gemini_data.get("hair_length", "medium"),
                "hair_style": gemini_data.get("hair_style", ""),
                "has_bangs": gemini_data.get("has_bangs", False),
                "skin_tone": gemini_data.get("skin_tone", "medium"),
                "ethnicity_hint": gemini_data.get("ethnicity", ""),
                "face_shape": gemini_data.get("face_shape", ""),
                "eye_shape": gemini_data.get("eye_shape", ""),
                "notable_features": gemini_data.get("notable_features", ""),
                "description": gemini_data.get("description_en", ""),
                "analysis_method": "gemini",
            }

            # If Gemini didn't provide a description, build one
            if not features["description"]:
                features["description"] = self._build_description(features)

            return features

        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
            return None

    def analyze(self, photos_dir: Path, sample_count: int = 10) -> dict:
        """
        分析照片文件夹，返回人物特征描述

        Returns: {
            "gender": "female" | "male",
            "age_range": "young" | "middle-aged" | "elderly",
            "age_avg": 25,
            "hair_color": "black" | "dark brown" | "brown" | "light brown" | "blonde" | "red" | "gray",
            "hair_length": "short" | "medium" | "long",
            "has_bangs": True | False,
            "skin_tone": "fair" | "medium" | "tan" | "dark",
            "ethnicity_hint": "Asian" | "European" | "other",
            "trigger_word": "sks",
            "description": "a young Asian woman with long dark hair and bangs",
            "folder_name": "girl",
        }
        """
        import cv2

        photos_dir = Path(photos_dir)
        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = sorted([f for f in photos_dir.iterdir() if f.suffix.lower() in photo_exts])

        if not photos:
            raise ValueError(f"No photos found in {photos_dir}")

        # ── Try Gemini Vision API first (best quality) ──
        gemini_result = self.analyze_with_gemini(photos_dir, sample_count=5)
        if gemini_result:
            gemini_result["photo_count"] = len(photos)
            gemini_result["folder_name"] = photos_dir.name
            logger.info(f"Identity analyzed via Gemini: {gemini_result.get('description', '')}")
            return gemini_result

        # ── Fallback: local InsightFace + OpenCV analysis ──
        logger.info("Using local analysis (InsightFace + OpenCV)")

        # Sample evenly across the folder
        step = max(1, len(photos) // sample_count)
        samples = photos[::step][:sample_count]

        # Collect features from InsightFace
        genders = []
        ages = []
        hair_colors_rgb = []
        skin_tones_rgb = []
        bangs_votes = []

        # Try InsightFace first for gender/age
        fd = None
        try:
            from src.pipeline.face_detector import FaceDetector
            fd = FaceDetector(device=self.device)
            fd.initialize()
        except Exception:
            pass

        for photo_path in samples:
            img = cv2.imread(str(photo_path))
            if img is None:
                continue

            h, w = img.shape[:2]

            # InsightFace analysis
            if fd is not None:
                try:
                    faces = fd.detect(img, max_faces=1)
                    if faces:
                        face = faces[0]
                        if face.gender:
                            genders.append(face.gender)
                        if face.age and face.age > 0:
                            ages.append(face.age)

                        # Extract hair and skin color from face bbox
                        x1, y1, x2, y2 = [int(v) for v in face.bbox]
                        face_w = x2 - x1
                        face_h = y2 - y1

                        # Skin tone: sample center of face
                        skin_cx = (x1 + x2) // 2
                        skin_cy = (y1 + y2) // 2
                        skin_r = max(1, face_w // 6)
                        skin_region = img[
                            max(0, skin_cy - skin_r):min(h, skin_cy + skin_r),
                            max(0, skin_cx - skin_r):min(w, skin_cx + skin_r)
                        ]
                        if skin_region.size > 0:
                            skin_tones_rgb.append(skin_region.mean(axis=(0, 1)))

                        # Hair color: sample region above face (narrower to avoid background)
                        hair_y1 = max(0, y1 - face_h // 2)
                        hair_y2 = y1
                        # Narrow sampling: only above the face center to avoid background
                        hair_x1 = max(0, x1 + face_w // 4)
                        hair_x2 = min(w, x2 - face_w // 4)
                        if hair_x2 > hair_x1 and hair_y2 > hair_y1:
                            hair_region = img[hair_y1:hair_y2, hair_x1:hair_x2]
                            if hair_region.size > 0:
                                # Use median instead of mean to ignore bright background outliers
                                import cv2 as _cv2
                                hair_median = np.median(hair_region.reshape(-1, 3), axis=0)
                                hair_colors_rgb.append(hair_median)

                        # Bangs detection: check if there are dark pixels on forehead
                        forehead_y1 = max(0, y1 - face_h // 3)
                        forehead_y2 = y1 + face_h // 6
                        forehead_cx1 = x1 + face_w // 4
                        forehead_cx2 = x2 - face_w // 4
                        forehead = img[forehead_y1:forehead_y2, forehead_cx1:forehead_cx2]
                        if forehead.size > 0:
                            forehead_brightness = forehead.mean()
                            # If forehead area is darker than skin, likely has bangs
                            skin_brightness = skin_region.mean() if skin_region.size > 0 else 150
                            bangs_votes.append(forehead_brightness < skin_brightness * 0.7)

                except Exception:
                    pass
            else:
                # OpenCV fallback: basic face detection
                try:
                    cascade = cv2.CascadeClassifier(
                        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                    )
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    detected = cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
                    if len(detected) > 0:
                        fx, fy, fw, fh = max(detected, key=lambda f: f[2] * f[3])
                        # Skin tone from face center
                        scx, scy = fx + fw // 2, fy + fh // 2
                        sr = max(1, fw // 6)
                        skin_r = img[max(0, scy - sr):min(h, scy + sr), max(0, scx - sr):min(w, scx + sr)]
                        if skin_r.size > 0:
                            skin_tones_rgb.append(skin_r.mean(axis=(0, 1)))
                        # Hair color above face
                        hair_r = img[max(0, fy - fh):fy, max(0, fx - fw // 4):min(w, fx + fw + fw // 4)]
                        if hair_r.size > 0:
                            hair_colors_rgb.append(hair_r.mean(axis=(0, 1)))
                except Exception:
                    pass

        if fd is not None:
            fd.release()

        # Analyze collected data
        result = {
            "trigger_word": "sks",
            "folder_name": photos_dir.name,
            "photo_count": len(photos),
        }

        # Gender
        if genders:
            female_count = sum(1 for g in genders if g == "F")
            male_count = sum(1 for g in genders if g == "M")
            result["gender"] = "female" if female_count >= male_count else "male"
        else:
            # Infer from folder name
            name_lower = photos_dir.name.lower()
            female_hints = ["girl", "woman", "female", "lady", "她", "女"]
            male_hints = ["boy", "man", "male", "guy", "他", "男"]
            if any(h in name_lower for h in female_hints):
                result["gender"] = "female"
            elif any(h in name_lower for h in male_hints):
                result["gender"] = "male"
            else:
                result["gender"] = "female"  # default

        # Age
        if ages:
            avg_age = sum(ages) / len(ages)
            result["age_avg"] = int(avg_age)
            if avg_age < 35:
                result["age_range"] = "young"
            elif avg_age < 50:
                result["age_range"] = "middle-aged"
            else:
                result["age_range"] = "elderly"
        else:
            result["age_range"] = "young"
            result["age_avg"] = 25

        # Hair color (BGR format from OpenCV)
        if hair_colors_rgb:
            avg_hair = np.mean(hair_colors_rgb, axis=0)  # BGR
            b, g, r = avg_hair
            brightness = (r + g + b) / 3
            # Classify hair color
            if brightness < 50:
                result["hair_color"] = "black"
            elif brightness < 80:
                if r > g and r > b:
                    result["hair_color"] = "dark brown"
                else:
                    result["hair_color"] = "black"
            elif brightness < 120:
                if r > b * 1.3:
                    result["hair_color"] = "brown"
                else:
                    result["hair_color"] = "dark brown"
            elif brightness < 160:
                if r > g * 1.2 and r > b * 1.5:
                    result["hair_color"] = "red"
                else:
                    result["hair_color"] = "light brown"
            elif brightness < 200:
                result["hair_color"] = "blonde"
            else:
                result["hair_color"] = "gray"
        else:
            result["hair_color"] = "dark"

        # Bangs
        if bangs_votes:
            result["has_bangs"] = sum(bangs_votes) > len(bangs_votes) / 2
        else:
            result["has_bangs"] = False

        # Skin tone
        if skin_tones_rgb:
            avg_skin = np.mean(skin_tones_rgb, axis=0)  # BGR
            skin_brightness = avg_skin.mean()
            if skin_brightness > 180:
                result["skin_tone"] = "fair"
            elif skin_brightness > 150:
                result["skin_tone"] = "light"
            elif skin_brightness > 120:
                result["skin_tone"] = "medium"
            elif skin_brightness > 90:
                result["skin_tone"] = "tan"
            else:
                result["skin_tone"] = "dark"
        else:
            result["skin_tone"] = "medium"

        # Ethnicity hint - use InsightFace embeddings + folder name + visual cues
        # Folder name hints are strong signals (user named the folder)
        name_lower = photos_dir.name.lower()
        asian_folder_hints = [
            "girl", "woman", "女", "日本", "japan", "asian", "中国", "china",
            "korean", "韓国", "台湾", "taiwan",
        ]
        has_asian_folder_hint = any(h in name_lower for h in asian_folder_hints)

        if has_asian_folder_hint:
            result["ethnicity_hint"] = "Asian"
        elif result["skin_tone"] in ("fair", "light") and result["hair_color"] in ("black", "dark brown"):
            result["ethnicity_hint"] = "Asian"
        elif result["skin_tone"] in ("fair",) and result["hair_color"] in ("blonde", "red"):
            result["ethnicity_hint"] = "European"
        else:
            # Don't guess - leave empty rather than guess wrong
            result["ethnicity_hint"] = ""

        # Build natural language description
        result["description"] = self._build_description(result)
        # Fix grammar: "a Asian" → "an Asian", "a elderly" → "an elderly"
        if result["description"].startswith("a ") and result["description"][2:3] in "AEIOUaeiou":
            result["description"] = "an " + result["description"][2:]

        return result

    def _build_description(self, features: dict) -> str:
        """从特征字典生成自然语言描述"""
        parts = []

        # Age + gender
        gender_word = "woman" if features["gender"] == "female" else "man"
        if features["age_range"] == "young":
            parts.append(f"young {gender_word}")
        elif features["age_range"] == "middle-aged":
            parts.append(f"{gender_word}")
        else:
            parts.append(f"elderly {gender_word}")

        # Ethnicity
        if features.get("ethnicity_hint"):
            parts[-1] = f"{features['ethnicity_hint']} " + parts[-1]

        # Hair
        hair_desc = features.get("hair_color", "dark") + " hair"
        if features.get("has_bangs"):
            hair_desc += " with bangs"
        parts.append(hair_desc)

        return "a " + ", ".join(parts)

    def generate_captions(self, features: dict, count: int = 8) -> list:
        """基于检测到的特征生成多样化的训练标注

        Uses richer Gemini features (hair_style, face_shape, eye_shape) when available.
        """
        tw = features["trigger_word"]
        desc = features.get("description", "a person")
        gender = "woman" if features.get("gender") == "female" else "man"
        hair = features.get("hair_color", "dark")
        hair_style = features.get("hair_style", "")
        bangs = ", bangs" if features.get("has_bangs") else ""
        face_shape = features.get("face_shape", "")
        eye_shape = features.get("eye_shape", "")

        # Build rich hair description
        hair_desc = f"{hair} hair"
        if hair_style:
            hair_desc = f"{hair} {hair_style} hair"
        elif bangs:
            hair_desc = f"{hair} hair with bangs"

        # Build face detail (from Gemini)
        face_detail = ""
        if face_shape and eye_shape:
            face_detail = f", {face_shape} face, {eye_shape} eyes"
        elif face_shape:
            face_detail = f", {face_shape} face"

        # Full image captions (varied descriptions using all available features)
        full_captions = [
            f"a photo of {tw} person, {desc}, high quality, detailed face, sharp focus",
            f"a portrait of {tw} person, {desc}, professional photography, studio lighting",
            f"a photo of {tw} person, {desc}, natural lighting, high resolution",
            f"{tw} person, {desc}, front view, high quality photograph, detailed",
            f"a professional photo of {tw} person, {gender} with {hair_desc}{face_detail}, detailed features, sharp",
            f"a photo of {tw} person, {desc}, clear face, well-lit, sharp focus",
            f"{tw} person, {gender}, {hair_desc}, high quality portrait, detailed",
            f"a studio photo of {tw} person, {desc}, professional, high resolution",
            f"a photo of {tw} person, {gender} with {hair_desc}{face_detail}, natural pose, detailed",
            f"{tw} person, {desc}, side view, professional photography, sharp",
        ]

        # Face close-up captions (emphasize facial features)
        face_captions = [
            f"a close up face photo of {tw} person, {desc}, detailed face{face_detail}, high quality, sharp focus",
            f"a headshot of {tw} person, {gender} with {hair_desc}{face_detail}, studio quality, detailed facial features",
            f"close up portrait of {tw} person, {desc}, clear face, professional photography",
            f"face of {tw} person, {gender}{face_detail}, {hair_desc}, macro detail, sharp focus",
            f"extreme close up of {tw} person face, {desc}, every detail visible, studio lighting",
        ]

        return full_captions[:count], face_captions[:max(2, count // 2)]


class LoRATrainer:
    """LoRA 微调训练器 - 本地 8GB VRAM 优化"""

    def __init__(self, device: str = "cuda", vram_limit_gb: float = 7.0):
        self.device = device
        self.vram_limit_gb = vram_limit_gb

    @staticmethod
    def auto_config(image_count: int, base_steps: int = 1500) -> dict:
        """根据训练图片数量自动调整LoRA参数

        Expert-validated configuration:
        - 少图(<30): 低rank避免过拟合, 低LR, 更多epochs
        - 中图(30-100): 标准配置
        - 多图(100+): 高rank增加容量, 标准LR
        """
        if image_count < 15:
            rank = 8
            lr = 5e-5
            steps = max(base_steps, image_count * 20)  # ~20 epochs
            alpha_mult = 1.5
            reason = f"少量图片({image_count}枚): 低rank防止过拟合, 低LR, 多epochs"
        elif image_count < 30:
            rank = 8
            lr = 8e-5
            steps = max(base_steps, image_count * 15)  # ~15 epochs
            alpha_mult = 1.5
            reason = f"少量図片({image_count}枚): rank=8, 控えめなLR"
        elif image_count < 100:
            rank = 16
            lr = 1e-4
            steps = max(base_steps, image_count * 10)  # ~10 epochs
            alpha_mult = 2.0
            reason = f"標準({image_count}枚): rank=16, 標準LR"
        elif image_count < 200:
            rank = 24
            lr = 1e-4
            steps = max(base_steps, image_count * 8)  # ~8 epochs
            alpha_mult = 2.0
            reason = f"大量({image_count}枚): rank=24, 高容量"
        else:
            rank = 32
            lr = 1e-4
            steps = max(base_steps, image_count * 6)  # ~6 epochs
            alpha_mult = 2.0
            reason = f"超大量({image_count}枚): rank=32, 最大容量"

        # Cap steps at reasonable max for 8GB VRAM (~30 min)
        steps = min(steps, 5000)

        return {
            "rank": rank,
            "lr": lr,
            "steps": steps,
            "alpha_multiplier": alpha_mult,
            "epochs_approx": round(steps / max(1, image_count), 1),
            "reason": reason,
            "image_count": image_count,
        }

    def prepare_training_data(
        self,
        photos_dir: Path,
        output_dir: Path,
        target_size: int = 512,
        auto_caption: bool = True,
        trigger_word: str = "sks",
        progress_callback: Optional[Callable] = None,
        identity_features: Optional[dict] = None,
    ) -> dict:
        """准备训练数据: 中心裁剪、人脸提取、基于身份特征的精准标注"""
        import cv2

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        img_dir = output_dir / "images"
        img_dir.mkdir(exist_ok=True)

        # Clean previous training data to avoid mixing identities
        for old_file in img_dir.glob("*"):
            old_file.unlink(missing_ok=True)

        photo_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        photos = sorted([
            f for f in Path(photos_dir).iterdir()
            if f.suffix.lower() in photo_exts
        ])

        if not photos:
            raise ValueError(f"写真が見つかりません: {photos_dir}")

        # Generate captions based on identity features (or use generic fallback)
        if identity_features:
            analyzer = IdentityAnalyzer()
            caption_templates, face_caption_templates = analyzer.generate_captions(identity_features)
            if progress_callback:
                progress_callback(f"身份特征: {identity_features.get('description', 'unknown')}")
        else:
            caption_templates = [
                f"a photo of {trigger_word} person, high quality, detailed face, sharp focus",
                f"a portrait of {trigger_word} person, professional photography, studio lighting",
                f"a photo of {trigger_word} person, natural lighting, high resolution, clear face",
                f"{trigger_word} person, front view, high quality photograph, detailed",
                f"a professional photo of {trigger_word} person, sharp, well-lit, detailed features",
            ]
            face_caption_templates = [
                f"a close up face photo of {trigger_word} person, detailed face, high quality, sharp focus",
                f"a headshot of {trigger_word} person, portrait, studio quality, detailed facial features",
                f"close up portrait of {trigger_word} person, clear face, professional photography",
            ]

        # Initialize face detector for face cropping
        face_cascade = None
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception:
            pass

        processed = 0
        face_crops = 0
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

                # === Full image: center-crop to square (no gray padding) ===
                crop_size = min(h, w)
                y_start = (h - crop_size) // 2
                x_start = (w - crop_size) // 2
                cropped = img[y_start:y_start + crop_size, x_start:x_start + crop_size]
                resized = cv2.resize(cropped, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

                out_path = img_dir / f"{processed:06d}.png"
                cv2.imwrite(str(out_path), resized)

                if auto_caption:
                    caption = caption_templates[processed % len(caption_templates)]
                    caption_path = img_dir / f"{processed:06d}.txt"
                    caption_path.write_text(caption, encoding="utf-8")

                processed += 1

                # === Face close-up crop (every 3rd image) for identity learning ===
                if face_cascade is not None and idx % 3 == 0:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
                    if len(faces) > 0:
                        # Get largest face
                        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                        # Expand crop area around face (2x padding for context)
                        pad = int(max(fw, fh) * 0.8)
                        fx1 = max(0, fx - pad)
                        fy1 = max(0, fy - pad)
                        fx2 = min(w, fx + fw + pad)
                        fy2 = min(h, fy + fh + pad)
                        face_img = img[fy1:fy2, fx1:fx2]

                        if face_img.size > 0:
                            # Center-crop face region to square
                            fh2, fw2 = face_img.shape[:2]
                            fcs = min(fh2, fw2)
                            fys = (fh2 - fcs) // 2
                            fxs = (fw2 - fcs) // 2
                            face_sq = face_img[fys:fys + fcs, fxs:fxs + fcs]
                            face_resized = cv2.resize(face_sq, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

                            face_path = img_dir / f"{processed:06d}.png"
                            cv2.imwrite(str(face_path), face_resized)

                            if auto_caption:
                                face_caption = face_caption_templates[face_crops % len(face_caption_templates)]
                                face_cap_path = img_dir / f"{processed:06d}.txt"
                                face_cap_path.write_text(face_caption, encoding="utf-8")

                            processed += 1
                            face_crops += 1

                if progress_callback and (idx + 1) % 50 == 0:
                    progress_callback(f"データ準備: {idx + 1}/{total} ({processed} 成功, 顔クロップ {face_crops})")

            except Exception as e:
                logger.debug(f"Skip {photo.name}: {e}")
                skipped += 1

        if progress_callback:
            progress_callback(f"データ準備完了: {processed} 枚 (顔クロップ {face_crops} 枚含む, {skipped} スキップ)")

        logger.info(f"Prepared {processed} training images ({face_crops} face crops) in {img_dir}")
        return {"count": processed, "face_crops": face_crops, "skipped": skipped, "path": str(img_dir)}

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
        steps, rank, lr, trigger_word, batch_size, callback=None,
    ) -> Path:
        """Real local training loop using diffusers + PEFT

        Key fixes for identity preservation:
        - Per-image captions with pre-computed text embeddings
        - Correct PEFT target_modules (module names, not paths)
        - Adaptive training steps based on dataset size
        - PEFT native save format for reliable loading
        """
        import torch
        from diffusers import AutoencoderKL, UNet2DConditionModel, DDPMScheduler
        from transformers import CLIPTextModel, CLIPTokenizer
        from peft import LoraConfig, get_peft_model
        from PIL import Image

        device = self.device
        dtype = torch.float16

        if callback:
            callback("モデルロード中...")

        # 1) Discover training images and their captions
        img_dir = Path(data_dir)
        image_files = sorted(img_dir.glob("*.png"))
        if not image_files:
            raise ValueError(f"No training images found in {img_dir}")

        # Limit images for 8GB VRAM
        max_images = min(len(image_files), 300)
        if len(image_files) > max_images:
            if callback:
                callback(f"注意: VRAM制限のため {max_images}/{len(image_files)} 枚のみ使用")
        image_files = image_files[:max_images]

        # Adaptive steps: at least 8 epochs for strong identity learning
        min_steps = max(steps, len(image_files) * 8)
        if min_steps > steps:
            if callback:
                callback(f"ステップ数を自動調整: {steps} → {min_steps} ({len(image_files)}枚 × 8エポック)")
            steps = min_steps

        # Read per-image captions from .txt files
        default_caption = f"a photo of {trigger_word} person, high quality, detailed"
        captions = []
        for img_path in image_files:
            txt_path = img_path.with_suffix(".txt")
            if txt_path.exists():
                cap = txt_path.read_text(encoding="utf-8").strip()
                captions.append(cap if cap else default_caption)
            else:
                captions.append(default_caption)

        # 2) Load tokenizer + text encoder → pre-compute embeddings for ALL unique captions
        tokenizer = CLIPTokenizer.from_pretrained(base_model, subfolder="tokenizer")
        text_encoder = CLIPTextModel.from_pretrained(
            base_model, subfolder="text_encoder", torch_dtype=dtype,
        ).to(device)

        unique_captions = list(set(captions))
        caption_to_embed = {}
        if callback:
            callback(f"テキスト埋め込み計算中... ({len(unique_captions)} 種類のキャプション)")

        for caption in unique_captions:
            tokens = tokenizer(
                caption, padding="max_length", max_length=tokenizer.model_max_length,
                truncation=True, return_tensors="pt",
            ).input_ids.to(device)
            with torch.no_grad():
                embed = text_encoder(tokens)[0].cpu()  # (1, 77, 768)
            caption_to_embed[caption] = embed

        # Build per-image embedding list (same order as image_files)
        image_embeds = [caption_to_embed[c] for c in captions]

        # Free text encoder VRAM
        del text_encoder, tokenizer
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback("VAE latents キャッシュ中...")

        # 3) Load VAE → cache latents → free VAE
        vae = AutoencoderKL.from_pretrained(
            base_model, subfolder="vae", torch_dtype=dtype,
        ).to(device)
        vae.eval()

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

        # 4) Load UNet → apply LoRA → prepare training
        unet = UNet2DConditionModel.from_pretrained(
            base_model, subfolder="unet", torch_dtype=dtype,
        ).to(device)

        unet.enable_gradient_checkpointing()

        # Apply LoRA - target attention + projection layers
        # PEFT matches by module NAME (final component), not full dotted path
        lora_config = LoraConfig(
            r=rank,
            lora_alpha=rank * 2,  # alpha/r = 2.0 for stronger identity
            target_modules=[
                "to_k", "to_q", "to_v", "to_out.0",  # attention layers
                "proj_in", "proj_out",  # transformer block projections
            ],
            lora_dropout=0.05,
        )
        unet = get_peft_model(unet, lora_config)

        trainable = sum(p.numel() for p in unet.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in unet.parameters())
        if callback:
            callback(f"LoRA パラメータ: {trainable:,} / {total_params:,} ({100*trainable/total_params:.2f}%)")

        # Noise scheduler
        noise_scheduler = DDPMScheduler.from_pretrained(base_model, subfolder="scheduler")

        # Optimizer - ONLY trainable params
        trainable_params = [p for p in unet.parameters() if p.requires_grad]
        try:
            import bitsandbytes as bnb
            optimizer = bnb.optim.AdamW8bit(trainable_params, lr=lr, weight_decay=1e-2)
            if callback:
                callback("オプティマイザ: AdamW 8bit (VRAM節約)")
        except Exception:
            optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=1e-2)
            if callback:
                callback("オプティマイザ: AdamW (標準)")

        # Mixed precision scaler
        scaler = torch.amp.GradScaler("cuda")

        # Learning rate scheduler - cosine annealing with warmup
        warmup_steps = min(100, steps // 10)
        lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=steps - warmup_steps, eta_min=lr * 0.1,
        )

        # 5) Training loop
        unet.train()
        num_latents = len(latent_cache)

        if callback:
            callback(f"学習開始: {steps} steps (warmup: {warmup_steps}, データ: {num_latents}枚)...")

        for step in range(steps):
            # Linear warmup
            if step < warmup_steps:
                warmup_lr = lr * (step + 1) / warmup_steps
                for pg in optimizer.param_groups:
                    pg['lr'] = warmup_lr

            # Random latent + MATCHING text embedding
            lat_idx = torch.randint(0, num_latents, (1,)).item()
            latent = latent_cache[lat_idx].to(device, dtype=dtype)
            text_embed = image_embeds[lat_idx].to(device, dtype=dtype)

            # Random noise + timestep
            noise = torch.randn_like(latent)
            timestep = torch.randint(
                0, noise_scheduler.config.num_train_timesteps, (1,), device=device
            ).long()

            noisy_latent = noise_scheduler.add_noise(latent, noise, timestep)

            # Forward pass
            with torch.amp.autocast("cuda"):
                noise_pred = unet(
                    noisy_latent, timestep,
                    encoder_hidden_states=text_embed,
                ).sample
                loss = torch.nn.functional.mse_loss(noise_pred.float(), noise.float())

            # Backward pass
            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(unet.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()

            if step >= warmup_steps:
                lr_scheduler.step()

            if callback and (step + 1) % 50 == 0:
                current_lr = optimizer.param_groups[0]['lr']
                callback(f"Step {step+1}/{steps} | Loss: {loss.item():.4f} | LR: {current_lr:.2e}")

            if (step + 1) % max(1, steps // 3) == 0:
                self._save_lora_diffusers(unet, output_dir / f"checkpoint-{step+1}")

        # 6) Save final weights
        if callback:
            callback("LoRA 重み保存中...")

        self._save_lora_diffusers(unet, output_dir)

        unet.eval()
        del optimizer, latent_cache, image_embeds, scaler, lr_scheduler
        torch.cuda.empty_cache()
        gc.collect()

        if callback:
            callback(f"LoRA 学習完了! 保存先: {output_dir}")

        return output_dir

    @staticmethod
    def _save_lora_diffusers(peft_unet, save_dir: Path):
        """Save LoRA weights in PEFT-native format (most compatible with diffusers load_lora_weights)"""
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Remove any old pytorch_lora_weights.safetensors that might conflict
        old_diffusers = save_dir / "pytorch_lora_weights.safetensors"
        if old_diffusers.exists():
            old_diffusers.unlink()

        try:
            # Use PEFT's native save_pretrained - produces adapter_model.safetensors + adapter_config.json
            # This is the most reliable format for diffusers load_lora_weights()
            peft_unet.save_pretrained(str(save_dir))
            logger.info(f"LoRA weights saved (PEFT native format): {save_dir}")
        except Exception as e:
            logger.warning(f"PEFT save_pretrained failed: {e}, trying manual save")
            try:
                from peft import get_peft_model_state_dict
                from safetensors.torch import save_file

                state_dict = get_peft_model_state_dict(peft_unet)
                # Clean up keys for diffusers compatibility
                diffusers_dict = {}
                for key, val in state_dict.items():
                    new_key = key.replace("base_model.model.", "")
                    # Remove adapter name (e.g. ".default") from key path
                    new_key = new_key.replace(".default", "")
                    diffusers_dict[new_key] = val.cpu()

                save_file(diffusers_dict, str(save_dir / "pytorch_lora_weights.safetensors"))
                logger.info(f"LoRA weights saved (manual diffusers format): {save_dir}")
            except Exception as e2:
                logger.error(f"All LoRA save methods failed: {e2}")
                raise


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
        """无姿势检测时使用OpenCV DNN人体姿势估计"""
        import cv2

        h, w = image.shape[:2]
        # Create black canvas for pose drawing (like OpenPose output)
        canvas = np.zeros((h, w, 3), dtype=np.uint8)

        # Use OpenCV's built-in person detector to find the person region
        # Then draw a simple stick figure based on body proportions
        # This is much better than Canny edges for ControlNet
        try:
            # Try OpenCV DNN pose estimation
            proto = cv2.data.haarcascades + "haarcascade_fullbody.xml"
            body_cascade = cv2.CascadeClassifier(proto)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bodies = body_cascade.detectMultiScale(gray, 1.1, 3)

            if len(bodies) > 0:
                # Draw person silhouette on black background
                bx, by, bw, bh = max(bodies, key=lambda b: b[2]*b[3])

                # Draw simplified stick figure
                cx = bx + bw // 2  # center x
                head_y = by + bh // 8
                neck_y = by + bh // 5
                hip_y = by + int(bh * 0.55)
                knee_y = by + int(bh * 0.78)
                foot_y = by + bh
                shoulder_w = bw // 3

                color = (255, 255, 255)
                thickness = max(2, min(w, h) // 150)

                # Head circle
                cv2.circle(canvas, (cx, head_y), bh // 10, color, thickness)
                # Spine
                cv2.line(canvas, (cx, neck_y), (cx, hip_y), color, thickness)
                # Shoulders
                cv2.line(canvas, (cx - shoulder_w, neck_y + 10), (cx + shoulder_w, neck_y + 10), color, thickness)
                # Arms
                cv2.line(canvas, (cx - shoulder_w, neck_y + 10), (cx - shoulder_w - bw//6, hip_y), color, thickness)
                cv2.line(canvas, (cx + shoulder_w, neck_y + 10), (cx + shoulder_w + bw//6, hip_y), color, thickness)
                # Legs
                cv2.line(canvas, (cx, hip_y), (cx - bw//4, knee_y), color, thickness)
                cv2.line(canvas, (cx, hip_y), (cx + bw//4, knee_y), color, thickness)
                cv2.line(canvas, (cx - bw//4, knee_y), (cx - bw//5, foot_y), color, thickness)
                cv2.line(canvas, (cx + bw//4, knee_y), (cx + bw//5, foot_y), color, thickness)

                return canvas
        except Exception:
            pass

        # Last resort: return black image with white center silhouette
        # ControlNet will generate a centered standing person
        cx, cy = w // 2, h // 2
        cv2.ellipse(canvas, (cx, cy - h//6), (w//8, h//4), 0, 0, 360, (255, 255, 255), 2)
        cv2.line(canvas, (cx, cy), (cx, cy + h//4), (255, 255, 255), 2)
        return canvas

    def release(self):
        self._detector = None
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass


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
        try:
            controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/control_v11p_sd15_openpose",
                torch_dtype=torch.float16,
            )
        except Exception as e:
            logger.error(f"ControlNet download/load failed: {e}")
            raise RuntimeError(
                "ControlNet モデルのダウンロードに失敗しました。"
                "ネットワーク接続を確認するか、手動でモデルをダウンロードしてください: "
                "lllyasviel/control_v11p_sd15_openpose"
            ) from e

        logger.info("Loading Stable Diffusion pipeline...")
        try:
            self._pipe = StableDiffusionControlNetPipeline.from_pretrained(
                base_model,
                controlnet=controlnet,
                torch_dtype=torch.float16,
                safety_checker=None,
            )
        except Exception as e:
            logger.error(f"SD pipeline load failed: {e}")
            raise RuntimeError(
                f"Stable Diffusion パイプラインのロードに失敗: {e}"
            ) from e

        self._pipe.scheduler = UniPCMultistepScheduler.from_config(
            self._pipe.scheduler.config
        )

        # Load LoRA BEFORE cpu_offload (offload hooks can interfere with weight injection)
        if lora_path and Path(lora_path).exists():
            lora_path = Path(lora_path)
            logger.info(f"Loading LoRA weights from: {lora_path}")
            try:
                self._pipe.load_lora_weights(str(lora_path))
                logger.info("LoRA weights loaded successfully")
            except Exception as lora_err:
                logger.warning(f"Standard LoRA load failed: {lora_err}")
                # Try loading individual safetensors file directly
                safetensors_files = list(lora_path.glob("*.safetensors"))
                if safetensors_files:
                    try:
                        self._pipe.load_lora_weights(str(safetensors_files[0]))
                        logger.info(f"LoRA loaded from file: {safetensors_files[0].name}")
                    except Exception as e2:
                        logger.error(f"All LoRA load attempts failed: {e2}")
                else:
                    logger.error("No safetensors files found in LoRA directory")

        # 8GB VRAM optimization (must be after LoRA loading)
        self._pipe.enable_model_cpu_offload()
        try:
            self._pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            logger.debug("xformers not available")

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

        # Ensure dimensions are divisible by 8 (required by VAE)
        width = (width // 8) * 8
        height = (height // 8) * 8

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
