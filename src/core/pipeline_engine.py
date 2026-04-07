"""
Pipeline Engine - 处理流水线编排
负责人: 首席架构师 (#1)
"""
import asyncio
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger("yovus.pipeline")


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    stage_name: str
    status: StageStatus
    message: str = ""
    output_path: Optional[Path] = None
    elapsed_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineJob:
    job_id: str
    source_video: Path
    reference_photos_dir: Path
    output_path: Path
    mode: str = "face_only"
    stages: list = field(default_factory=list)
    current_stage: int = 0
    total_progress: float = 0.0
    status: str = "pending"
    results: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    # 共享数据: 各阶段通过此字典传递中间结果
    shared_data: dict = field(default_factory=dict)


class PipelineEngine:
    """核心流水线引擎"""

    STAGE_DEFINITIONS = {
        "face_only": [
            ("video_decode", "映像解析", 0.05),
            ("face_detect_reference", "参照顔検出", 0.10),
            ("face_swap", "顔交換", 0.50),
            ("face_enhance", "顔補正", 0.15),
            ("video_encode", "映像合成", 0.15),
            ("post_process", "後処理", 0.05),
        ],
        "face_and_body": [
            ("video_decode", "映像解析", 0.05),
            ("face_detect_reference", "参照顔検出", 0.05),
            ("pose_estimate", "姿勢推定", 0.10),
            ("body_segment", "人物分割", 0.10),
            ("face_swap", "顔交換", 0.20),
            ("body_generate", "身体生成", 0.20),
            ("composite", "合成融合", 0.10),
            ("face_enhance", "顔補正", 0.05),
            ("video_encode", "映像合成", 0.10),
            ("post_process", "後処理", 0.05),
        ],
        "full_replace": [
            ("video_decode", "映像解析", 0.03),
            ("face_detect_reference", "参照顔検出", 0.05),
            ("lora_train", "LoRAモデル学習", 0.15),
            ("pose_estimate", "姿勢推定", 0.07),
            ("body_segment", "人物分割", 0.05),
            ("inpaint_mask", "Inpaint マスク生成", 0.05),
            ("face_swap", "顔交換", 0.12),
            ("body_generate", "身体生成（ControlNet）", 0.18),
            ("composite", "合成融合", 0.08),
            ("face_enhance", "顔補正", 0.05),
            ("temporal_smooth", "時間軸平滑化", 0.05),
            ("video_encode", "映像合成", 0.07),
            ("post_process", "後処理", 0.05),
        ],
        "cloud": [
            ("upload_reference", "参照写真アップロード", 0.10),
            ("cloud_train", "クラウド学習", 0.30),
            ("cloud_swap", "クラウド置換処理", 0.40),
            ("download_result", "結果ダウンロード", 0.15),
            ("post_process", "後処理", 0.05),
        ],
    }

    def __init__(self):
        self._stage_handlers: dict[str, Callable] = {}
        self._progress_callback: Optional[Callable] = None
        self._log_callback: Optional[Callable] = None
        self._current_job: Optional[PipelineJob] = None
        self._cancel_flag = False

    def register_stage(self, stage_name: str, handler: Callable):
        self._stage_handlers[stage_name] = handler

    def set_progress_callback(self, callback: Callable):
        self._progress_callback = callback

    def set_log_callback(self, callback: Callable):
        self._log_callback = callback

    def _log(self, message: str, level: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        logger.info(message)
        if self._log_callback:
            try:
                self._log_callback(formatted, level)
            except TypeError:
                # Fallback: callback may only accept one arg
                self._log_callback(formatted)

    def _update_progress(self, progress: float, stage_name: str = ""):
        if self._progress_callback:
            try:
                self._progress_callback(progress, stage_name)
            except Exception:
                pass

    def cancel(self):
        self._cancel_flag = True
        self._log("処理をキャンセル中...")

    def run_sync(self, job: PipelineJob) -> list:
        """同步运行 (避免Gradio事件循环冲突)"""
        self._current_job = job
        self._cancel_flag = False
        job.status = "running"
        job.stages = self.STAGE_DEFINITIONS.get(job.mode, self.STAGE_DEFINITIONS["face_only"])
        results = []
        cumulative_weight = 0.0

        self._log(f"パイプライン開始: {job.mode} モード | {len(job.stages)}ステージ")

        for i, (stage_id, stage_label, weight) in enumerate(job.stages):
            if self._cancel_flag:
                self._log("ユーザーによりキャンセルされました")
                results.append(StageResult(stage_id, StageStatus.SKIPPED, "Cancelled"))
                break

            job.current_stage = i
            self._log(f"[{i+1}/{len(job.stages)}] {stage_label} 開始...")
            self._update_progress(cumulative_weight, stage_label)

            handler = self._stage_handlers.get(stage_id)
            if not handler:
                self._log(f"  -- {stage_id} ハンドラ未登録 - スキップ")
                results.append(StageResult(stage_id, StageStatus.SKIPPED, "No handler"))
                cumulative_weight += weight
                continue

            start_time = time.time()
            try:
                output = handler(job, results)

                elapsed = time.time() - start_time
                result = StageResult(
                    stage_name=stage_id,
                    status=StageStatus.COMPLETED,
                    message=f"{stage_label} 完了",
                    elapsed_seconds=elapsed,
                    metadata=output if isinstance(output, dict) else {},
                )
                results.append(result)
                cumulative_weight += weight
                self._log(f"  OK {stage_label} 完了 ({elapsed:.1f}s)")

            except Exception as e:
                elapsed = time.time() - start_time
                result = StageResult(
                    stage_name=stage_id,
                    status=StageStatus.FAILED,
                    message=str(e),
                    elapsed_seconds=elapsed,
                )
                results.append(result)
                self._log(f"  NG {stage_label} エラー: {e}")
                job.status = "failed"
                break

        if not self._cancel_flag and job.status != "failed":
            job.status = "completed"
            self._update_progress(1.0, "完了")
            self._log("パイプライン完了!")

        job.results = results
        self._current_job = None
        return results

    def get_stage_info(self, mode: str) -> list[dict]:
        stages = self.STAGE_DEFINITIONS.get(mode, [])
        return [
            {"id": sid, "label": label, "weight": weight}
            for sid, label, weight in stages
        ]
