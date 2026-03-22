#!/usr/bin/env bash
# ==========================================
#   悠数 · 电商财务管理系统 - 一键启动
#   适用于 macOS / Linux
# ==========================================
set -e
cd "$(dirname "$0")"

echo ""
echo "  ╔══════════════════════════════╗"
echo "  ║   悠数 · 电商财务管理系统    ║"
echo "  ╚══════════════════════════════╝"
echo ""

# 检查 Python 版本
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(sys.version_info >= (3, 11))" 2>/dev/null)
        if [ "$ver" = "True" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  ❌ 需要 Python 3.11 或更高版本"
    echo ""
    echo "  Mac 安装方式 (任选其一):"
    echo "    1. brew install python@3.13"
    echo "    2. 官网下载: https://www.python.org/downloads/"
    echo ""
    exit 1
fi
echo "  ✅ Python: $($PYTHON --version)"

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "  [1/4] 创建虚拟环境..."
    $PYTHON -m venv .venv
else
    echo "  [1/4] 虚拟环境已存在 ✅"
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
if [ ! -f ".venv/.installed" ]; then
    echo "  [2/4] 安装依赖 (首次较慢，请耐心等待)..."
    pip install -q --upgrade pip 2>&1 | grep -v "already satisfied" || true
    pip install -e . 2>&1 | grep -v "already satisfied" | tail -3
    touch .venv/.installed
    echo "         依赖安装完成 ✅"
else
    echo "  [2/4] 依赖已安装 ✅"
fi

# 初始化数据库
echo "  [3/4] 初始化数据库..."
python -c "
import asyncio
from app.database import engine, Base
from app.models import order, finance, reconciliation, platform_fee, tax, budget, product
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
print('         数据库就绪 ✅')
"

# 自动打开浏览器 (后台延迟2秒)
(sleep 2 && {
    if command -v open &>/dev/null; then
        open "http://localhost:8080"
    elif command -v xdg-open &>/dev/null; then
        xdg-open "http://localhost:8080"
    fi
} &>/dev/null) &

# 启动服务
echo "  [4/4] 启动服务..."
echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │                                         │"
echo "  │   🌐 浏览器打开: http://localhost:8080   │"
echo "  │   📄 API 文档:   http://localhost:8080/docs │"
echo "  │                                         │"
echo "  │   按 Ctrl+C 停止服务                    │"
echo "  └─────────────────────────────────────────┘"
echo ""

uvicorn app.main:app --host 127.0.0.1 --port 8080
