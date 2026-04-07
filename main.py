"""
YOVUS - AI映像人物置換システム
メインエントリーポイント
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("yovus")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """启动 YOVUS 系统"""
    from src.config.settings import config

    logger.info("=" * 50)
    logger.info("  YOVUS - AI映像人物置換システム v1.0")
    logger.info("=" * 50)

    # Ensure directories
    config.paths.ensure_dirs()

    # GPU Detection
    from src.core.gpu_manager import GPUManager
    gpu = GPUManager()
    info = gpu.detect()
    if info.is_available:
        logger.info(f"GPU: {info.name} ({info.vram_total_mb}MB VRAM)")
    else:
        logger.warning("GPU未検出。CPU処理モードで動作します。")

    recommendations = gpu.get_recommended_settings()
    logger.info(f"推奨: {recommendations.get('message', '')}")

    # Launch UI
    from src.ui.app import create_app
    app = create_app()

    logger.info(f"サーバー起動中... http://localhost:{config.server_port}")
    app.launch(
        server_name="0.0.0.0",
        server_port=config.server_port,
        share=config.share,
        show_api=False,
        favicon_path=None,
    )


if __name__ == "__main__":
    main()
