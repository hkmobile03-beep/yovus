"""Convenience launcher: ``python main.py -s face.jpg -t in.mp4 -o out.mp4``."""

from face_swap.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
