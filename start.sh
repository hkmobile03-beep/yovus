#!/usr/bin/env bash
# 悠数 · 电商财务系统 一键启动脚本
set -e

echo "==============================="
echo "  悠数 · 电商财务管理系统"
echo "==============================="
echo ""

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "错误: 需要 Python 3.10+"
    exit 1
fi

# 安装依赖
echo "[1/3] 安装依赖..."
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic-settings python-multipart aiofiles python-jose bcrypt anthropic 2>/dev/null | tail -1

# 初始化数据库
echo "[2/3] 初始化数据库..."
python3 -c "
import asyncio
from app.database import engine, Base
from app.models import order, finance, reconciliation, platform_fee, tax, budget, product
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
" 2>/dev/null

echo "[3/3] 启动服务..."
echo ""
echo "  浏览器打开: http://localhost:8080"
echo "  API 文档:   http://localhost:8080/docs"
echo ""
echo "  按 Ctrl+C 停止服务"
echo "==============================="
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8080
