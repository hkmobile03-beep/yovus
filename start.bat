@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════╗
echo   ║   悠数 · 电商财务管理系统    ║
echo   ╚══════════════════════════════╝
echo.

:: 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo   错误: 未找到 Python，请安装 Python 3.11+
    echo   下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   %%v

:: 创建虚拟环境
if not exist ".venv" (
    echo   [1/4] 创建虚拟环境...
    python -m venv .venv
) else (
    echo   [1/4] 虚拟环境已存在
)

:: 激活虚拟环境
call .venv\Scripts\activate.bat

:: 安装依赖
echo   [2/4] 安装依赖...
pip install -q --upgrade pip
pip install -q -e . 2>nul

:: 初始化数据库
echo   [3/4] 初始化数据库...
python -c "import asyncio; from app.database import engine, Base; from app.models import order, finance, reconciliation, platform_fee, tax, budget, product; asyncio.run((lambda: (yield))() or asyncio.ensure_future(_init())); " 2>nul
python -c "import asyncio; from app.database import engine, Base; from app.models import order, finance, reconciliation, platform_fee, tax, budget, product; exec('async def f():\n async with engine.begin() as c:\n  await c.run_sync(Base.metadata.create_all)'); asyncio.run(f())" 2>nul
echo          数据库就绪

:: 启动
echo   [4/4] 启动服务...
echo.
echo   ┌─────────────────────────────────────┐
echo   │                                     │
echo   │   浏览器打开: http://localhost:8080  │
echo   │   API 文档:   http://localhost:8080/docs
echo   │                                     │
echo   │   按 Ctrl+C 停止                    │
echo   └─────────────────────────────────────┘
echo.

uvicorn app.main:app --host 127.0.0.1 --port 8080
pause
