"""AI 分析 API 端点"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.services.ai_service import AIAnalysisService

router = APIRouter(prefix="/ai", tags=["AI分析"])


@router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_data(
    request: AIAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """AI 智能分析接口

    根据用户问题和指定的分析上下文，聚合相关财务数据并生成分析报告。
    支持的 context_type: general, orders, reconciliation, tax, profit
    """
    service = AIAnalysisService(db)
    result = await service.analyze(
        question=request.question,
        context_type=request.context_type,
        period=request.period,
    )
    return result
