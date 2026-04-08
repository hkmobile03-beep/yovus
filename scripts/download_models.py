"""
YOVUS 模型下载脚本
"""
import os
import sys
from pathlib import Path

# Model registry
MODELS = {
    "inswapper_128": {
        "url": "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx",
        "filename": "inswapper_128.onnx",
        "size": "500MB",
        "required": True,
        "description": "顔交換コアモデル (InsightFace)",
    },
    "GFPGANv1.4": {
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        "filename": "GFPGANv1.4.pth",
        "size": "330MB",
        "required": False,
        "description": "顔復元・補正モデル",
    },
    "RealESRGAN_x2plus": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "filename": "RealESRGAN_x2plus.pth",
        "size": "64MB",
        "required": False,
        "description": "超解像モデル (x2)",
    },
}

MODELS_DIR = Path(__file__).parent.parent / "models"


def download_file(url: str, filepath: Path, description: str = ""):
    """下载文件并显示进度（使用临时文件防止损坏）"""
    try:
        import httpx
    except ImportError:
        print("  ⚠ httpx not installed. Install: pip install httpx")
        print(f"  手動ダウンロード: {url}")
        return

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_path = filepath.with_suffix(".downloading")

    print(f"\nダウンロード中: {description}")
    print(f"  URL: {url}")
    print(f"  保存先: {filepath}")

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as response:
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")
            total = int(response.headers.get("content-length", 0))
            if tqdm:
                pbar = tqdm(total=total, unit="B", unit_scale=True, desc=filepath.name)
            with open(temp_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    if tqdm and pbar:
                        pbar.update(len(chunk))
            if tqdm and pbar:
                pbar.close()

        # Verify file is not too small (error pages)
        if temp_path.stat().st_size < 1_000_000:
            temp_path.unlink()
            raise RuntimeError(f"Downloaded file too small, likely an error page")

        # Rename temp file to final (atomic on same filesystem)
        temp_path.rename(filepath)
        print(f"  ✓ 完了: {filepath.name}")

    except Exception as e:
        # Clean up partial download
        if temp_path.exists():
            temp_path.unlink()
        raise e


def main():
    print("=" * 50)
    print("  YOVUS モデルダウンローダー")
    print("=" * 50)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    required_only = "--required" in sys.argv

    for name, info in MODELS.items():
        if required_only and not info["required"]:
            continue

        filepath = MODELS_DIR / info["filename"]
        if filepath.exists():
            # Check for corrupt files (e.g. saved error pages)
            if filepath.stat().st_size < 1_000_000:
                print(f"\n⚠ {name}: ファイル破損 (サイズ異常)。再ダウンロードします。")
                filepath.unlink()
            else:
                print(f"\n✓ {name}: インストール済み ({info['filename']})")
                continue

        try:
            download_file(info["url"], filepath, info["description"])
        except Exception as e:
            print(f"\n✗ {name}: ダウンロード失敗 - {e}")
            print(f"  手動ダウンロード: {info['url']}")
            print(f"  保存先: {filepath}")

    print("\n" + "=" * 50)
    print("  ダウンロード完了")
    print("=" * 50)

    # Check buffalo_l (InsightFace auto-downloads)
    print("\n注意: InsightFace (buffalo_l) モデルは初回使用時に自動ダウンロードされます。")
    print("注意: Stable Diffusion / ControlNet モデルは diffusers が自動ダウンロードします。")


if __name__ == "__main__":
    main()
