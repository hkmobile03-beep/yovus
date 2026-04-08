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


def run_pip(*args, quiet=False):
    """Run a pip command and return (success, output)."""
    cmd = [sys.executable, "-m", "pip"] + list(args)
    result = subprocess.run(
        cmd, capture_output=quiet, text=True,
    )
    stdout = result.stdout if quiet else ""
    return result.returncode == 0, stdout


def check_system():
    """检查系统环境"""
    print("[1/7] システム確認中...")
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
    print("[2/7] GPU確認中...")
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
    print("[3/7] FFmpeg確認中...")
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
    print("[4/7] PyTorch (CUDA) インストール中...")
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
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("  ✓ PyTorch CUDA インストール完了")
    else:
        print("  ⚠ PyTorch インストール失敗。手動でインストールしてください:")
        print(f"    {' '.join(cmd)}")
    print()


def install_build_tools():
    """Install C++ build prerequisites for packages that need compilation (e.g. insightface)."""
    print("[5/7] ビルドツール確認中...")

    if platform.system() != "Windows":
        print("  ✓ Linux/Mac — スキップ")
        print()
        return

    # Install Cython and numpy first (insightface build deps)
    print("  Cython/numpy をインストール中 (ビルド依存)...")
    run_pip("install", "cython", "numpy", quiet=True)

    # Check if MSVC (cl.exe) is available
    cl_found = False
    try:
        result = subprocess.run(
            ["where", "cl.exe"], capture_output=True, text=True, timeout=10,
        )
        cl_found = result.returncode == 0
    except Exception:
        pass

    if cl_found:
        print("  ✓ C++ コンパイラ検出済み (MSVC)")
    else:
        print("  ⚠ C++ コンパイラが見つかりません")
        print("  → insightface のビルドに必要です")
        print("  → 以下の方法で解決できます:")
        print()
        print("    方法1 (推奨): Visual Studio Build Tools をインストール")
        print("      https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("      → 「C++ によるデスクトップ開発」にチェックしてインストール")
        print()
        print("    方法2: winget でインストール")
        print("      winget install Microsoft.VisualStudio.2022.BuildTools")
        print()
        print("  ※ Build Tools インストール後、このスクリプトを再実行してください")
        print("  ※ Build Tools がなくても ONNX フォールバックで動作可能です")
    print()


def install_insightface():
    """Install insightface with multiple fallback strategies."""
    print("[6/7] InsightFace インストール中...")

    # Check if already installed
    try:
        import insightface
        print(f"  ✓ InsightFace {insightface.__version__} インストール済み")
        print()
        return True
    except ImportError:
        pass

    # Strategy 1: Try pre-built wheel (fastest)
    print("  試行 1/3: プリビルドホイールを検索中...")
    ok, _ = run_pip(
        "install", "insightface>=0.7.3", "--only-binary", ":all:", quiet=True,
    )
    if ok:
        print("  ✓ InsightFace プリビルドインストール完了")
        print()
        return True
    print("  → プリビルドホイールなし")

    # Strategy 2: Install build deps then build from source
    print("  試行 2/3: ソースからビルド中...")
    # Ensure build deps are present
    run_pip("install", "cython", "numpy", "setuptools", "wheel", quiet=True)
    ok, _ = run_pip("install", "insightface>=0.7.3", "--no-build-isolation", quiet=True)
    if ok:
        print("  ✓ InsightFace ソースビルド完了")
        print()
        return True
    print("  → ソースビルド失敗")

    # Strategy 3: Try older version that may have wheels
    print("  試行 3/3: 旧バージョン (0.7.3) を試行中...")
    ok, _ = run_pip("install", "insightface==0.7.3", quiet=True)
    if ok:
        print("  ✓ InsightFace 0.7.3 インストール完了")
        print()
        return True

    # All strategies failed
    print()
    print("  ╔════════════════════════════════════════════════╗")
    print("  ║  ⚠ InsightFace インストール失敗                 ║")
    print("  ╚════════════════════════════════════════════════╝")
    print()
    print("  原因: Windows で C++ コンパイラが見つかりません")
    print()
    print("  ■ 解決方法 (推奨):")
    print("    1. Visual Studio Build Tools をインストール:")
    print("       https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("       → 「C++ によるデスクトップ開発」にチェック")
    print("    2. PC を再起動")
    print("    3. このスクリプトを再実行: python scripts/install.py")
    print()
    print("  ■ InsightFace なしでも動作します:")
    print("    → 顔検出: OpenCV Cascade (フォールバック)")
    print("    → 顔替換: ONNX Runtime 直接推論 (フォールバック)")
    print("    → 品質は少し下がりますが、基本機能は使えます")
    print()
    return False


def install_requirements():
    """安装其他依赖 (excluding insightface which is handled separately)"""
    print("[6.5/7] その他の依存パッケージインストール中...")
    req_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")

    if not os.path.exists(req_file):
        print(f"  ✗ requirements.txt が見つかりません: {req_file}")
        return

    # Read requirements and filter out insightface (handled separately)
    with open(req_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    filtered = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("insightface"):
            continue
        filtered.append(line)

    # Write temp requirements file without insightface
    temp_req = req_file + ".tmp"
    with open(temp_req, "w", encoding="utf-8") as f:
        f.writelines(filtered)

    cmd = [sys.executable, "-m", "pip", "install", "-r", temp_req]
    print(f"  実行: pip install -r requirements.txt (insightface除外)")
    result = subprocess.run(cmd)

    # Clean up temp file
    try:
        os.remove(temp_req)
    except OSError:
        pass

    if result.returncode == 0:
        print("  ✓ 依存パッケージインストール完了")
    else:
        print("  ⚠ 一部のパッケージのインストールに失敗しました")
    print()


def create_directories():
    """创建必要目录"""
    print("[7/7] ディレクトリ作成中...")
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
    install_build_tools()
    install_insightface()
    install_requirements()
    create_directories()
    print_next_steps()


if __name__ == "__main__":
    main()
