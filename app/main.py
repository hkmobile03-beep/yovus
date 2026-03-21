"""中国电商财务对账系统 - 主入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.config import settings

app = FastAPI(
    title="电商财务对账系统",
    description="""
    ## 中国电商财务对账系统

    面向天猫/京东电商卖家的一站式财务管理系统，包含：

    - **核算模块**：订单流水、收入确认（价税分离）、成本核算、自动生成会计凭证
    - **对账模块**：导入平台结算账单，自动匹配订单，识别差异
    - **税务模块**：增值税（一般纳税人）、企业所得税、附加税计算与申报数据
    - **利润分析**：整体利润、SKU级利润、各平台渠道ROI
    - **预算预警**：预算编制与执行跟踪、自定义预警规则

    ### 支持平台
    - 天猫/淘宝（支付宝结算）
    - 京东POP/自营

    ### 纳税人类型
    - 一般纳税人（增值税13%/9%/6%，可抵扣进项税）
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(v1_router)


@app.get("/")
async def root():
    return {
        "system": "中国电商财务对账系统",
        "version": "0.1.0",
        "modules": [
            "核算模块 - /api/v1/orders",
            "对账模块 - /api/v1/reconciliation",
            "税务模块 - /api/v1/tax",
            "利润分析 - /api/v1/analytics",
            "预算预警 - /api/v1/alerts",
        ],
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
