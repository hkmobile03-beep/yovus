"""
Install Facefusion for high-quality local video face swap.

Clones Facefusion into external/facefusion and installs its dependencies.
Facefusion = inswapper_128 + face enhancer (GFPGAN/CodeFormer) + occlusion aware
face swap + temporal smoothing. It is the gold standard for free local video
face swap.

Usage:
  python scripts/setup_facefusion.py                   # CUDA (default, recommended)
  python scripts/setup_facefusion.py --provider cpu    # CPU only
  python scripts/setup_facefusion.py --force-clean     # Re-clone from scratch
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "external"
FACEFUSION_DIR = EXTERNAL_DIR / "facefusion"
FACEFUSION_REPO = "https://github.com/facefusion/facefusion.git"


def run(cmd, cwd=None, check=True):
    shown = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    print(f"  $ {shown}")
    result = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str))
    if check and result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        sys.exit(1)
    return result.returncode


def check_git():
    if shutil.which("git") is None:
        print("  ERROR: git is not installed. Install from https://git-scm.com")
        sys.exit(1)


def clone_or_update(force_clean: bool):
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    if force_clean and FACEFUSION_DIR.exists():
        print(f"\n[clean] Removing existing {FACEFUSION_DIR}")
        shutil.rmtree(FACEFUSION_DIR, ignore_errors=True)

    if not FACEFUSION_DIR.exists():
        print(f"\n[1/3] Cloning Facefusion into {FACEFUSION_DIR} ...")
        run(["git", "clone", "--depth", "1", FACEFUSION_REPO, str(FACEFUSION_DIR)])
    else:
        print(f"\n[1/3] Facefusion already cloned, pulling latest ...")
        run(["git", "pull", "--ff-only"], cwd=FACEFUSION_DIR, check=False)


def install_dependencies(provider: str):
    print(f"\n[2/3] Installing Facefusion dependencies (provider={provider}) ...")

    installer = FACEFUSION_DIR / "install.py"
    if installer.exists():
        # Facefusion ships its own installer that knows about onnxruntime variants
        # --skip-conda tells it to use the current pip env instead of conda
        run(
            [sys.executable, "install.py", "--onnxruntime", provider, "--skip-conda"],
            cwd=FACEFUSION_DIR,
            check=False,
        )
        return

    # Fallback: plain pip install of requirements.txt
    req = FACEFUSION_DIR / "requirements.txt"
    if req.exists():
        run([sys.executable, "-m", "pip", "install", "-r", str(req)])
    else:
        print("  WARNING: no install.py or requirements.txt found in facefusion")


def verify():
    print(f"\n[3/3] Verifying Facefusion installation ...")
    entry = FACEFUSION_DIR / "facefusion.py"
    if not entry.exists():
        print(f"  ERROR: {entry} not found")
        sys.exit(1)

    # A quick --help call confirms the CLI loads without import errors
    rc = run(
        [sys.executable, "facefusion.py", "--help"],
        cwd=FACEFUSION_DIR,
        check=False,
    )
    if rc != 0:
        print("  WARNING: facefusion --help returned non-zero. Dependencies may be")
        print("  incomplete. Check messages above. You can still try running swaps;")
        print("  missing packages will surface on first run.")
        return

    print("\n  Facefusion ready.")
    print(f"  Install path: {FACEFUSION_DIR}")
    print()
    print("  Next step:")
    print("    python scripts/video_faceswap_pro.py <input_video> <reference_photo_or_folder>")
    print()
    print("  Models will auto-download on first run (a few GB to ~/.facefusion).")


def main():
    parser = argparse.ArgumentParser(description="Install Facefusion for YOVUS")
    parser.add_argument(
        "--provider",
        choices=["cuda", "cpu", "directml", "openvino", "rocm"],
        default="cuda",
        help="ONNXRuntime execution provider (default: cuda)",
    )
    parser.add_argument(
        "--force-clean",
        action="store_true",
        help="Remove external/facefusion before cloning",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Facefusion Setup for YOVUS")
    print("=" * 60)

    check_git()
    clone_or_update(args.force_clean)
    install_dependencies(args.provider)
    verify()


if __name__ == "__main__":
    main()
