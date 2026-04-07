# YOVUS - AI Video Person Replacement System
# YOVUS - AI映像人物置換システム

> 全身人物替换 | 动作保持 | 1000+参考照片训练 | 日系极简UI

## 系统架构 - 10人虚拟AI工程团队

| # | 角色 | 负责模块 | 技术栈 |
|---|------|---------|--------|
| 1 | **首席架构师** | 系统总设计、Pipeline编排 | Python, Gradio, asyncio |
| 2 | **视频工程师** | 视频解码/编码/帧提取 | FFmpeg, OpenCV, PyAV |
| 3 | **人脸检测专家** | 人脸检测/对齐/特征提取 | InsightFace, RetinaFace |
| 4 | **人脸替换专家** | 人脸交换核心引擎 | FaceFusion, inswapper |
| 5 | **姿态估计专家** | 人体骨骼/姿态提取 | DWPose, OpenPose, MMPose |
| 6 | **生成模型专家** | LoRA训练/ControlNet推理 | Stable Diffusion, kohya |
| 7 | **图像融合专家** | 图像混合/边缘处理/色彩校正 | OpenCV, Poisson Blending |
| 8 | **后处理专家** | 超分辨率/去噪/帧间一致性 | CodeFormer, Real-ESRGAN |
| 9 | **UI/UX设计师** | 日系界面/交互设计 | Gradio, CSS, HTML |
| 10 | **DevOps工程师** | 部署/GPU优化/内存管理 | CUDA, ONNX, TensorRT |

## 处理流水线

```
原始视频 → 帧提取 → 人物检测 → 姿态估计 ─┐
                                            ├→ 人脸替换 → 全身融合 → 后处理 → 视频合成
参考照片(1000+) → 人脸提取 → 模型训练 ────┘
```

## 硬件要求

- **最低**: RTX 3060 (8GB VRAM)
- **推荐**: RTX 4070+ (12GB+ VRAM)  
- **当前**: RTX 5070 Laptop (8GB VRAM) ✓ 可运行

## 快速开始

```bash
# 1. 安装依赖
python scripts/install.py

# 2. 启动系统
python main.py

# 3. 打开浏览器访问 http://localhost:7860
```
