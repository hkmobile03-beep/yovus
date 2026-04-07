"""
人脸检测与对齐模块 (修复版)
负责人: 人脸检测专家 (#3)

Bug修复:
- 添加初始化状态追踪，避免重复初始化
- 添加进度回调给 extract_best_references
- 修复 embedding 为 None 时的相似度计算
- 增强 Windows 路径兼容
"""
import logging
from pathlib import Path
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger("yovus.face_detect")


class FaceData:
    """人脸数据容器"""
    __slots__ = ['bbox', 'landmarks', 'score', 'embedding', 'age', 'gender', 'aligned_face', '_raw']

    def __init__(self, bbox=(0, 0, 0, 0), landmarks=None, score=0.0,
                 embedding=None, age=0, gender="", aligned_face=None, raw=None):
        self.bbox = bbox
        self.landmarks = landmarks
        self.score = score
        self.embedding = embedding
        self.age = age
        self.gender = gender
        self.aligned_face = aligned_face
        self._raw = raw  # 保存 insightface 原始 Face 对象


class FaceDetector:
    """人脸检测 + 特征提取"""

    def __init__(self, detector_type: str = "retinaface", device: str = "cuda"):
        self.detector_type = detector_type
        self.device = device
        self._detector = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        try:
            import insightface
            from insightface.app import FaceAnalysis

            self._detector = FaceAnalysis(
                name="buffalo_l",
                providers=self._get_providers(),
            )
            self._detector.prepare(ctx_id=0, det_size=(640, 640))
            self._initialized = True
            logger.info(f"Face detector initialized: InsightFace buffalo_l")
        except ImportError:
            logger.warning("InsightFace not installed, using OpenCV fallback")
            self._init_fallback()
        except Exception as e:
            logger.warning(f"InsightFace init error: {e}, using fallback")
            self._init_fallback()

    def _init_fallback(self):
        import cv2
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._detector = cv2.CascadeClassifier(cascade_path)
        if self._detector.empty():
            logger.error("OpenCV cascade classifier failed to load")
        self.detector_type = "opencv_cascade"
        self._initialized = True

    def detect(self, image: np.ndarray, max_faces: int = 5) -> list:
        """检测图像中的人脸"""
        if not self._initialized:
            self.initialize()

        if self.detector_type == "opencv_cascade":
            return self._detect_opencv(image, max_faces)

        try:
            faces = self._detector.get(image)
            faces = sorted(faces, key=lambda f: f.det_score, reverse=True)[:max_faces]

            results = []
            for face in faces:
                fd = FaceData(
                    bbox=tuple(int(x) for x in face.bbox),
                    landmarks=face.kps if hasattr(face, 'kps') else None,
                    score=float(face.det_score),
                    embedding=face.embedding if hasattr(face, 'embedding') else None,
                    age=int(face.age) if hasattr(face, 'age') else 0,
                    gender="M" if hasattr(face, 'gender') and face.gender == 1 else "F",
                    raw=face,  # 保存原始 Face 对象供 inswapper 使用
                )
                results.append(fd)

            return results

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    def _detect_opencv(self, image: np.ndarray, max_faces: int) -> list:
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        detections = self._detector.detectMultiScale(gray, 1.3, 5)
        results = []
        for (x, y, w, h) in detections[:max_faces]:
            results.append(FaceData(bbox=(x, y, x + w, y + h), score=0.8))
        return results

    def extract_best_references(
        self,
        photos_dir: Path,
        max_count: int = 50,
        min_score: float = 0.65,
        progress_callback: Optional[Callable] = None,
    ) -> list:
        """从1000+张参考照片中提取最佳人脸"""
        import cv2

        if not self._initialized:
            self.initialize()

        all_faces = []
        photo_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        photos_path = Path(photos_dir)
        if not photos_path.exists():
            logger.error(f"Photos directory not found: {photos_dir}")
            return []

        photo_files = sorted([
            f for f in photos_path.iterdir()
            if f.suffix.lower() in photo_extensions
        ])

        if not photo_files:
            logger.warning(f"No photos found in {photos_dir}")
            return []

        total = len(photo_files)
        logger.info(f"Scanning {total} photos for face extraction...")

        for i, photo_path in enumerate(photo_files):
            try:
                # Windows路径兼容
                img = cv2.imread(str(photo_path))
                if img is None:
                    continue

                faces = self.detect(img, max_faces=1)
                if faces and faces[0].score >= min_score:
                    face = faces[0]
                    all_faces.append({
                        "path": str(photo_path),
                        "face_data": face,
                        "score": face.score,
                        "image_size": (img.shape[1], img.shape[0]),
                    })

                if progress_callback and (i + 1) % 20 == 0:
                    progress_callback(f"スキャン中: {i + 1}/{total} ({len(all_faces)} 顔検出)")

            except Exception as e:
                logger.debug(f"Skip {photo_path.name}: {e}")

        if progress_callback:
            progress_callback(f"スキャン完了: {total} 枚中 {len(all_faces)} 顔検出")

        # Sort by quality
        all_faces.sort(key=lambda x: x["score"], reverse=True)

        if len(all_faces) > max_count:
            step = max(1, len(all_faces) // max_count)
            selected = [all_faces[i * step] for i in range(min(max_count, len(all_faces) // step))]
        else:
            selected = all_faces

        logger.info(f"Selected {len(selected)} best reference faces")
        return selected

    def compute_similarity(self, embedding1, embedding2) -> float:
        if embedding1 is None or embedding2 is None:
            return 0.0
        e1 = np.asarray(embedding1, dtype=np.float32).flatten()
        e2 = np.asarray(embedding2, dtype=np.float32).flatten()
        if e1.shape != e2.shape:
            return 0.0
        norm1 = np.linalg.norm(e1)
        norm2 = np.linalg.norm(e2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(np.dot(e1, e2) / (norm1 * norm2))

    def _get_providers(self) -> list:
        if self.device == "cuda":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def release(self):
        self._detector = None
        self._initialized = False
        logger.info("Face detector released")
