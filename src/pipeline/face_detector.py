"""
人脸检测与对齐模块
负责人: 人脸检测专家 (#3)
"""
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("yovus.face_detect")


@dataclass
class FaceData:
    bbox: tuple = (0, 0, 0, 0)  # x1, y1, x2, y2
    landmarks: Optional[np.ndarray] = None  # 5-point or 68-point
    score: float = 0.0
    embedding: Optional[np.ndarray] = None
    age: int = 0
    gender: str = ""
    aligned_face: Optional[np.ndarray] = None  # 112x112 aligned crop


class FaceDetector:
    """
    人脸检测 + 特征提取
    支持: RetinaFace, SCRFD, YOLOFace
    """

    def __init__(self, detector_type: str = "retinaface", device: str = "cuda"):
        self.detector_type = detector_type
        self.device = device
        self._detector = None
        self._recognizer = None

    def initialize(self):
        """延迟初始化模型（节省VRAM）"""
        try:
            import insightface
            from insightface.app import FaceAnalysis

            self._detector = FaceAnalysis(
                name="buffalo_l",
                providers=self._get_providers(),
            )
            self._detector.prepare(ctx_id=0, det_size=(640, 640))
            logger.info(f"Face detector initialized: {self.detector_type}")
        except ImportError:
            logger.warning("InsightFace not installed. Using fallback detector.")
            self._init_fallback()

    def _init_fallback(self):
        """OpenCV fallback detector"""
        import cv2
        self._detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.detector_type = "opencv_cascade"

    def detect(self, image: np.ndarray, max_faces: int = 5) -> list[FaceData]:
        """检测图像中的人脸"""
        if self._detector is None:
            self.initialize()

        if self.detector_type == "opencv_cascade":
            return self._detect_opencv(image, max_faces)

        try:
            faces = self._detector.get(image)
            faces = sorted(faces, key=lambda f: f.det_score, reverse=True)[:max_faces]

            results = []
            for face in faces:
                fd = FaceData(
                    bbox=tuple(face.bbox.astype(int)),
                    landmarks=face.kps if hasattr(face, 'kps') else None,
                    score=float(face.det_score),
                    embedding=face.embedding if hasattr(face, 'embedding') else None,
                    age=int(face.age) if hasattr(face, 'age') else 0,
                    gender="M" if hasattr(face, 'gender') and face.gender == 1 else "F",
                )
                results.append(fd)

            return results

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    def _detect_opencv(self, image: np.ndarray, max_faces: int) -> list[FaceData]:
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detections = self._detector.detectMultiScale(gray, 1.3, 5)
        results = []
        for (x, y, w, h) in detections[:max_faces]:
            results.append(FaceData(
                bbox=(x, y, x + w, y + h),
                score=1.0,
            ))
        return results

    def extract_best_references(
        self,
        photos_dir: Path,
        max_count: int = 50,
        min_score: float = 0.7,
    ) -> list[dict]:
        """
        从1000+张参考照片中提取最佳人脸
        返回按质量排序的人脸列表
        """
        import cv2

        if self._detector is None:
            self.initialize()

        all_faces = []
        photo_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        photo_files = [
            f for f in Path(photos_dir).iterdir()
            if f.suffix.lower() in photo_extensions
        ]

        logger.info(f"Scanning {len(photo_files)} photos for face extraction...")

        for i, photo_path in enumerate(photo_files):
            try:
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

                if (i + 1) % 100 == 0:
                    logger.info(f"  Scanned {i + 1}/{len(photo_files)} photos, found {len(all_faces)} faces")

            except Exception as e:
                logger.debug(f"Skip {photo_path.name}: {e}")

        # Sort by quality and diversity
        all_faces.sort(key=lambda x: x["score"], reverse=True)

        if len(all_faces) > max_count:
            # Select diverse subset: pick evenly from sorted list
            step = len(all_faces) // max_count
            selected = [all_faces[i * step] for i in range(max_count)]
        else:
            selected = all_faces

        logger.info(f"Selected {len(selected)} reference faces from {len(all_faces)} detected")
        return selected

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算两个人脸嵌入的相似度"""
        if embedding1 is None or embedding2 is None:
            return 0.0
        from numpy.linalg import norm
        return float(np.dot(embedding1, embedding2) / (norm(embedding1) * norm(embedding2)))

    def _get_providers(self) -> list:
        if self.device == "cuda":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def release(self):
        self._detector = None
        self._recognizer = None
        logger.info("Face detector released")
