"""
YOVUS 一键安装脚本
针对 Windows + RTX 5070 Laptop (8GB) 优化
"""
import os
import sys
import subprocess
import platform


def print_header():
    print("=" * 56)
    print("  YOVUS - AI映像人物置換システム インストーラー")
    print("=" * 56)
    print()


def check_system():
    """检查系统环境"""
    print("[1/6] システム確認中...")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version}")
    print(f"  Platform: {platform.machine()}")

    if sys.version_info < (3, 10):
        print("  ✗ Python 3.10以上が必要です")
        sys.exit(1)
    print("  ✓ Python バージョン OK")
    print()


def check_gpu():
    """检查GPU"""
    print("[2/6] GPU確認中...")
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            gpu_info = result.stdout.strip()
            print(f"  ✓ GPU検出: {gpu_info}")
        else:
            print("  ⚠ nvidia-smi実行失敗。GPUドライバを確認してください。")
    except FileNotFoundError:
        print("  ⚠ nvidia-smi が見つかりません。NVIDIAドライバをインストールしてください。")
    except Exception as e:
        print(f"  ⚠ GPU確認エラー: {e}")
    print()


def check_ffmpeg():
    """检查FFmpeg"""
    print("[3/6] FFmpeg確認中...")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0]
            print(f"  ✓ {version_line}")
        else:
            print("  ✗ FFmpegが見つかりません")
            print("  → https://ffmpeg.org/download.html からダウンロードしてください")
            print("  → Windows: winget install ffmpeg")
    except FileNotFoundError:
        print("  ✗ FFmpegが見つかりません")
        print("  → Windows: winget install ffmpeg")
        print("  → または https://ffmpeg.org/download.html")
    print()


def install_pytorch():
    """安装PyTorch (CUDA)"""
    print("[4/6] PyTorch (CUDA) インストール中...")
    print("  RTX 5070 Laptop → CUDA 12.4+ 推奨")

    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✓ PyTorch {torch.__version__} (CUDA {torch.version.cuda}) インストール済み")
            print(f"  ✓ GPU: {torch.cuda.get_device_name(0)}")
            return
        else:
            print("  ⚠ PyTorchはCPUモード。CUDA版を再インストールします。")
    except ImportError:
        pass

    cmd = [
        sys.executable, "-m", "pip", "install",
        "torch", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu124",
    ]
    print(f"  実行: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("  ✓ PyTorch CUDA インストール完了")
    print()


def install_requirements():
    """安装其他依赖"""
    print("[5/6] 依存パッケージインストール中...")
    req_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")

    if not os.path.exists(req_file):
        print(f"  ✗ requirements.txt が見つかりません: {req_file}")
        return

    cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]
    print(f"  実行: pip install -r requirements.txt")
    subprocess.run(cmd, check=True)
    print("  ✓ 依存パッケージインストール完了")
    print()


def create_directories():
    """创建必要目录"""
    print("[6/6] ディレクトリ作成中...")
    dirs = ["models", "temp", "output", "cache"]
    base = os.path.dirname(os.path.dirname(__file__))
    for d in dirs:
        path = os.path.join(base, d)
        os.makedirs(path, exist_ok=True)
        print(f"  ✓ {d}/")
    print()


def print_next_steps():
    print("=" * 56)
    print("  インストール完了!")
    print("=" * 56)
    print()
    print("次のステップ:")
    print()
    print("  1. モデルダウンロード (初回のみ):")
    print("     UIの「モデル」タブから一括ダウンロード")
    print("     または手動:")
    print("     - inswapper_128.onnx → models/")
    print("     - GFPGANv1.4.pth → models/")
    print("     - buffalo_l (InsightFace) → 自動ダウンロード")
    print()
    print("  2. アプリ起動:")
    print("     python main.py")
    print()
    print("  3. ブラウザでアクセス:")
    print("     http://localhost:7860")
    print()
    print("  4. 参照写真フォルダを設定:")
    print("     C:\\Users\\junqi\\Desktop\\test")
    print()


def main():
    print_header()
    check_system()
    check_gpu()
    check_ffmpeg()
    install_pytorch()
    install_requirements()
    create_directories()
    print_next_steps()


if __name__ == "__main__":
    main()
