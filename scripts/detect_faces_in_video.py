"""
视频人物检测预览 - 提取视频中所有人脸，让用户选择要替换的目标
"""
import sys
import cv2
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def detect_faces_in_video(video_path: str, sample_count: int = 5):
    """从视频中采样几帧，检测所有人脸并保存预览"""
    from src.pipeline.face_detector import FaceDetector

    output_dir = PROJECT_ROOT / "output" / "face_preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: Cannot open video: {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {w}x{h} @ {fps:.1f}fps, {total_frames} frames")

    # Initialize face detector
    fd = FaceDetector(device="cuda")
    fd.initialize()
    print("Face detector ready\n")

    # Sample frames evenly across the video
    sample_indices = [int(i * total_frames / (sample_count + 1)) for i in range(1, sample_count + 1)]

    all_faces = {}  # face_id -> list of crops

    for sample_idx, frame_idx in enumerate(sample_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        time_sec = frame_idx / fps
        print(f"--- Frame {frame_idx} (time: {time_sec:.1f}s) ---")

        # Detect faces
        faces = fd.detect(frame, max_faces=10)
        print(f"  Found {len(faces)} face(s)")

        if not faces:
            continue

        # Save the full frame with face boxes drawn
        frame_annotated = frame.copy()
        for i, face in enumerate(faces):
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            # Draw box
            color = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0), (0, 255, 255)][i % 5]
            cv2.rectangle(frame_annotated, (x1, y1), (x2, y2), color, 3)
            # Label
            label = f"Person {i} (score: {face.score:.2f})"
            cv2.putText(frame_annotated, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            print(f"  Person {i}: bbox=({x1},{y1})-({x2},{y2}), score={face.score:.2f}")

            # Crop face with some padding
            pad_x = int((x2 - x1) * 0.3)
            pad_y = int((y2 - y1) * 0.3)
            cx1 = max(0, x1 - pad_x)
            cy1 = max(0, y1 - pad_y)
            cx2 = min(w, x2 + pad_x)
            cy2 = min(h, y2 + pad_y)
            face_crop = frame[cy1:cy2, cx1:cx2]

            if face_crop.size > 0:
                # Resize for display
                face_crop = cv2.resize(face_crop, (256, 256))
                crop_path = output_dir / f"person_{i}_frame_{sample_idx}.png"
                cv2.imwrite(str(crop_path), face_crop)

                if i not in all_faces:
                    all_faces[i] = []
                all_faces[i].append(crop_path)

        # Save annotated frame (resize for readability)
        display_w = min(w, 1920)
        display_h = int(h * display_w / w)
        frame_display = cv2.resize(frame_annotated, (display_w, display_h))
        frame_path = output_dir / f"frame_{sample_idx}_annotated.png"
        cv2.imwrite(str(frame_path), frame_display)
        print(f"  Saved: {frame_path}")

    cap.release()
    fd.release()

    # Create a summary grid for each person
    print(f"\n{'='*50}")
    print(f"RESULTS: Found {len(all_faces)} person(s)")
    print(f"{'='*50}")

    for person_id, crops in all_faces.items():
        # Create grid of this person's face across frames
        grid_images = []
        for crop_path in crops[:5]:
            img = cv2.imread(str(crop_path))
            if img is not None:
                grid_images.append(cv2.resize(img, (200, 200)))

        if grid_images:
            grid = np.hstack(grid_images)
            grid_path = output_dir / f"person_{person_id}_grid.png"
            cv2.imwrite(str(grid_path), grid)
            print(f"\nPerson {person_id}:")
            print(f"  Preview grid: {grid_path}")
            print(f"  Appeared in {len(crops)} sampled frames")

    print(f"\nAll previews saved to: {output_dir}")
    print(f"\n--- NEXT STEP ---")
    print(f"1. Open {output_dir} and check each person's grid")
    print(f"2. Note the Person number you want to replace")
    print(f"3. Use that number as 'Target Face Index' in Processing tab")
    print(f"   Or run: python scripts/preview_lora.py to check LoRA quality first")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/detect_faces_in_video.py <video_path>")
        print("Example: python scripts/detect_faces_in_video.py C:\\path\\to\\video.mp4")
        sys.exit(1)

    detect_faces_in_video(sys.argv[1])
