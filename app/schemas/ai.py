from pydantic import BaseModel


class AIAnalysisRequest(BaseModel):
    question: str
    context_type: str = "general"
    period: str | None = None


class AIAnalysisResponse(BaseModel):
    analysis: str
    suggestions: list[str] = []
    data_points: list[dict] = []
