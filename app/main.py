"""中国电商财务对账系统 - 主入口"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as v1_router

STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="电商财务对账系统",
    description="""
    ## 中国电商财务对账系统

    面向天猫/京东电商卖家的一站式财务管理系统，包含：

    - **核算模块**：订单流水、收入确认（价税分离）、成本核算、自动生成会计凭证
    - **双口径收入对账**：创建订单口径（商家/ERP）与确认收货口径（平台涉税推送）随时切换对比
    - **对账模块**：导入平台结算账单，自动匹配订单，识别差异
    - **平台费用发票匹配**：跟踪佣金/推广费/技术服务费的发票状态，区分有票抵扣与无票分类
    - **税务模块**：增值税（一般纳税人）、企业所得税、附加税计算与申报数据
    - **利润分析**：整体利润、SKU级利润、各平台渠道ROI
    - **预算预警**：预算编制与执行跟踪、自定义预警规则

    ### 支持平台
    - 淘宝（主营）/ 天猫（支付宝结算）
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


@app.get("/health")
async def health():
    return {"status": "healthy"}


# 前端静态文件服务
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback - 所有非 API 路由返回 index.html"""
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:

    @app.get("/")
    async def root():
        return {
            "system": "中国电商财务对账系统",
            "version": "0.1.0",
            "docs": "/docs",
        }
