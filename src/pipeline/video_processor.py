"""
视频处理模块 (修复版)
负责人: 视频工程师 (#2)

Bug修复:
- 修复 ffprobe 不存在时的异常处理
- 添加 shutil.which 检查 ffmpeg
- 修复 Windows 路径兼容
- 添加进度回调
"""
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Generator, Callable
from dataclasses import dataclass

logger = logging.getLogger("yovus.video")


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


@dataclass
class VideoInfo:
    path: Path = None
    width: int = 0
    height: int = 0
    fps: float = 30.0
    frame_count: int = 0
    duration: float = 0.0
    codec: str = ""
    has_audio: bool = False
    file_size_mb: float = 0.0


class VideoProcessor:
    """视频解码/编码处理器"""

    def __init__(self, temp_dir: Path):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._has_ffmpeg = _ffmpeg_available()
        if not self._has_ffmpeg:
            logger.warning("FFmpeg not found. Video encoding will not work. Install: https://ffmpeg.org")

    def probe(self, video_path: Path) -> VideoInfo:
        """获取视频信息"""
        import cv2

        video_path = Path(video_path)
        info = VideoInfo(path=video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"映像ファイルが見つかりません: {video_path}")

        info.file_size_mb = video_path.stat().st_size / (1024 * 1024)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"映像ファイルを開けません: {video_path}")

        info.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        info.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        info.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        info.frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        info.duration = info.frame_count / info.fps if info.fps > 0 else 0
        info.codec = self._fourcc_to_str(int(cap.get(cv2.CAP_PROP_FOURCC)))
        cap.release()

        info.has_audio = self._check_audio(video_path)

        logger.info(
            f"Video: {info.width}x{info.height} @ {info.fps:.1f}fps, "
            f"{info.frame_count} frames, {info.duration:.1f}s"
        )
        return info

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Optional[Path] = None,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        step: int = 1,
        progress_callback: Optional[Callable] = None,
    ) -> Path:
        """提取视频帧到目录"""
        import cv2

        video_path = Path(video_path)
        if output_dir is None:
            output_dir = self.temp_dir / "frames" / video_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"映像を開けません: {video_path}")

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if end_frame is None:
            end_frame = total

        frame_idx = 0
        saved = 0
        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        while frame_idx < end_frame - start_frame:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % step == 0:
                out_path = output_dir / f"{start_frame + frame_idx:08d}.png"
                cv2.imwrite(str(out_path), frame)
                saved += 1

                if progress_callback and saved % 30 == 0:
                    progress_callback(f"フレーム抽出: {saved} / ~{(end_frame - start_frame) // step}")

            frame_idx += 1

        cap.release()
        logger.info(f"Extracted {saved} frames to {output_dir}")
        return output_dir

    def iterate_frames(self, video_path: Path) -> Generator:
        """逐帧迭代器（节省内存）"""
        import cv2

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"映像を開けません: {video_path}")

        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                yield frame_idx, frame
                frame_idx += 1
        finally:
            cap.release()

    def encode_video(
        self,
        frames_dir: Path,
        output_path: Path,
        fps: float = 30.0,
        codec: str = "libx264",
        crf: int = 18,
        audio_source: Optional[Path] = None,
    ) -> Path:
        """将帧序列编码为视频"""
        if not self._has_ffmpeg:
            # Fallback: use OpenCV VideoWriter
            return self._encode_opencv(frames_dir, output_path, fps)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 检测帧文件格式
        frame_pattern = str(frames_dir / "%08d.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", frame_pattern,
            "-c:v", codec,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-preset", "slow",
        ]

        if audio_source and Path(audio_source).exists() and self._check_audio(Path(audio_source)):
            cmd.extend([
                "-i", str(audio_source),
                "-c:a", "aac", "-b:a", "192k",
                "-map", "0:v", "-map", "1:a",
                "-shortest",
            ])

        cmd.append(str(output_path))

        logger.info(f"Encoding video: {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr[:300]}")
            # Fallback
            return self._encode_opencv(frames_dir, output_path, fps)

        logger.info(f"Video encoded: {output_path}")
        return output_path

    def _encode_opencv(self, frames_dir: Path, output_path: Path, fps: float) -> Path:
        """OpenCV 编码兜底"""
        import cv2

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        frames = sorted(Path(frames_dir).glob("*.png"))
        if not frames:
            raise ValueError(f"No frames found in {frames_dir}")

        first = cv2.imread(str(frames[0]))
        h, w = first.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

        for frame_path in frames:
            frame = cv2.imread(str(frame_path))
            if frame is not None:
                writer.write(frame)

        writer.release()
        logger.info(f"Video encoded (OpenCV): {output_path}")
        return output_path

    def extract_audio(self, video_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """提取音频轨道"""
        if not self._has_ffmpeg or not self._check_audio(Path(video_path)):
            return None

        if output_path is None:
            output_path = self.temp_dir / "audio" / f"{Path(video_path).stem}.aac"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "copy", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        output_path = Path(output_path)
        return output_path if output_path.exists() else None

    def _check_audio(self, video_path: Path) -> bool:
        if not _ffprobe_available():
            return False
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                str(video_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return "audio" in result.stdout
        except Exception:
            return False

    @staticmethod
    def _fourcc_to_str(fourcc: int) -> str:
        try:
            return "".join(chr((fourcc >> (8 * i)) & 0xFF) for i in range(4))
        except (ValueError, OverflowError):
            return "unknown"
