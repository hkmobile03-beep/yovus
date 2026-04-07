"""
视频处理模块 - 解码/编码/帧提取
负责人: 视频工程师 (#2)
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass

logger = logging.getLogger("yovus.video")


@dataclass
class VideoInfo:
    path: Path
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
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def probe(self, video_path: Path) -> VideoInfo:
        """获取视频信息"""
        import cv2

        info = VideoInfo(path=video_path)
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

        # Check audio via ffprobe
        info.has_audio = self._check_audio(video_path)

        logger.info(
            f"Video: {info.width}x{info.height} @ {info.fps:.1f}fps, "
            f"{info.frame_count} frames, {info.duration:.1f}s, "
            f"audio={info.has_audio}"
        )
        return info

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Optional[Path] = None,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        step: int = 1,
    ) -> Path:
        """提取视频帧到目录"""
        import cv2

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
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        while frame_idx < end_frame - start_frame:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % step == 0:
                out_path = output_dir / f"{start_frame + frame_idx:08d}.png"
                cv2.imwrite(str(out_path), frame)
                saved += 1
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
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            yield frame_idx, frame
            frame_idx += 1

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
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "%08d.png"),
            "-c:v", codec,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-preset", "slow",
        ]

        if audio_source and self._check_audio(audio_source):
            cmd.extend(["-i", str(audio_source), "-c:a", "aac", "-b:a", "192k", "-map", "0:v", "-map", "1:a", "-shortest"])

        cmd.append(str(output_path))

        logger.info(f"Encoding video: {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed: {result.stderr[:500]}")

        logger.info(f"Video encoded: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f}MB)")
        return output_path

    def extract_audio(self, video_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
        """提取音频轨道"""
        if not self._check_audio(video_path):
            return None

        if output_path is None:
            output_path = self.temp_dir / "audio" / f"{video_path.stem}.aac"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "copy", str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path if output_path.exists() else None

    def _check_audio(self, video_path: Path) -> bool:
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return "audio" in result.stdout
        except Exception:
            return False

    @staticmethod
    def _fourcc_to_str(fourcc: int) -> str:
        return "".join(chr((fourcc >> (8 * i)) & 0xFF) for i in range(4))
