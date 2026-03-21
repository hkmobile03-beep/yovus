"""对账管理API"""

from datetime import date
from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.reconciliation import (
    ReconciliationSummary,
    ReconciliationTaskCreate,
    ReconciliationTaskResponse,
)
from app.services.platform import JDParser, TmallParser
from app.services.reconciliation_service import ReconciliationService

router = APIRouter()


@router.post("/tasks", response_model=ReconciliationTaskResponse)
async def create_reconciliation_task(
    data: ReconciliationTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建对账任务"""
    service = ReconciliationService(db)
    task = await service.create_reconciliation_task(
        platform_id=data.platform_id,
        period_start=data.period_start,
        period_end=data.period_end,
    )
    return task


@router.post("/tasks/{task_id}/import-statement/{platform_type}")
async def import_and_reconcile(
    task_id: int,
    platform_type: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """导入平台账单并执行对账

    流程：
    1. 上传平台结算账单文件
    2. 解析账单数据
    3. 自动匹配系统订单
    4. 生成对账结果
    """
    from sqlalchemy import select
    from app.models.reconciliation import ReconciliationTask

    # 验证任务存在
    result = await db.execute(
        select(ReconciliationTask).where(ReconciliationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="对账任务不存在")

    parsers = {
        "tmall": TmallParser(),
        "taobao": TmallParser(),
        "jd": JDParser(),
    }
    parser = parsers.get(platform_type)
    if not parser:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform_type}")

    # 保存并解析文件
    suffix = Path(file.filename).suffix if file.filename else ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        platform_records = parser.parse_settlement(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    # 执行对账
    service = ReconciliationService(db)
    result = await service.reconcile_orders(task, platform_records)

    return {
        "task_id": task_id,
        "result": result,
        "message": f"对账完成，匹配率: {result['match_rate']}",
    }


@router.get("/tasks/{task_id}/summary", response_model=ReconciliationSummary)
async def get_reconciliation_summary(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取对账汇总报告"""
    service = ReconciliationService(db)
    return await service.get_reconciliation_summary(task_id)
