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
    echo "  错误: 需要 Python 3.11 或更高版本"
    echo "  请安装: https://www.python.org/downloads/"
    exit 1
fi
echo "  Python: $($PYTHON --version)"

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "  [1/4] 创建虚拟环境..."
    $PYTHON -m venv .venv
else
    echo "  [1/4] 虚拟环境已存在"
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo "  [2/4] 安装依赖..."
pip install -q --upgrade pip
pip install -q -e . 2>&1 | tail -1

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
print('         数据库就绪')
" 2>/dev/null

# 启动服务
echo "  [4/4] 启动服务..."
echo ""
echo "  ┌─────────────────────────────────────┐"
echo "  │                                     │"
echo "  │   浏览器打开: http://localhost:8080  │"
echo "  │   API 文档:   http://localhost:8080/docs"
echo "  │                                     │"
echo "  │   按 Ctrl+C 停止                    │"
echo "  └─────────────────────────────────────┘"
echo ""

uvicorn app.main:app --host 127.0.0.1 --port 8080
