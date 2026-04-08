"""
YOVUS - AI映像人物置換システム v2.0
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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """启动 YOVUS 系统"""
    from src.config.settings import config

    logger.info("=" * 50)
    logger.info("  YOVUS v2.0 - AI映像人物置換システム")
    logger.info("  Local & Cloud Processing")
    logger.info("=" * 50)

    # 显式初始化 (创建目录等)
    config.initialize()

    # GPU Detection
    from src.core.gpu_manager import GPUManager
    gpu = GPUManager()
    info = gpu.detect()
    if info.is_available:
        logger.info(f"GPU: {info.name} ({info.vram_total_mb}MB VRAM)")
    else:
        logger.warning("GPU not detected. CPU-only mode.")

    rec = gpu.get_recommended_settings()
    logger.info(f"Recommendation: {rec.get('message', '')}")

    # Launch UI
    from src.ui.app import create_app
    app = create_app()

    logger.info(f"Server starting at http://localhost:{config.server_port}")
    app.launch(
        server_name="0.0.0.0",
        server_port=config.server_port,
        share=config.share,
    )


if __name__ == "__main__":
    main()
