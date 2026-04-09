# yovus — Hybrid Video Face Swap

本地识别 + fal.ai 云端换脸。流程:

1. 用 **InsightFace** 在本地扫描目标视频,识别视频中出现的所有人物
2. 把人物聚类成"person_00 / person_01 / ..."并输出预览缩略图,你选要换的那个
3. 从你给的**参考照片文件夹**里自动挑一张正脸、清晰度最高的当 source
4. 如果视频分辨率高于 1080p(比如 4K),**本地 ffmpeg 先缩成 1080p**再上传
5. 调用 **fal.ai `fal-ai/pixverse/swap`** 端点执行换脸
6. 下载结果到本地

本工具**不**在本地跑 inswapper,只在本地做识别 + 预处理。

---

## 安装

```bash
pip install -r requirements.txt
```

系统依赖:需要 `ffmpeg`(用于分辨率缩放和音频保留)。

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

InsightFace 的 `buffalo_l` 模型会在第一次运行时自动下载到 `~/.insightface/`。

---

## 配置 fal API key

到 [fal.ai](https://fal.ai) 申请 API key,然后导出:

```bash
export FAL_KEY="your_fal_api_key_here"
```

---

## 使用

### 当前标准方案(Pixverse 720p)

这是目前验证过、端到端跑通的方案。**4K 输入本地先缩到 ≤1080p 且 ≤1920
一边**(Pixverse 硬上限),然后云端用 Pixverse `person` 模式换脸,输出
**720p**(Pixverse 现在的最高档,1080p 已被拒)。

PowerShell:

```powershell
cd C:\Users\junqi\Desktop\yovus
python main.py `
    -t "C:\Users\junqi\Desktop\yovus\yovus.mov" `
    -s "C:\Users\junqi\Desktop\girl" `
    -o "C:\Users\junqi\Desktop\yovus_swapped_720p.mp4" `
    --max-height 1080 `
    --resolution 720p `
    --yes
```

Linux / macOS:

```bash
python main.py \
    --target /path/to/input.mp4 \
    --source-folder /path/to/new_person_photos/ \
    --output /path/to/output.mp4 \
    --max-height 1080 \
    --resolution 720p \
    --yes
```

运行过程:

```
[target] input.mp4  3840x2160  25.00 fps  62.3s
[local] loading InsightFace (buffalo_l)...
[local] scanning video at 1.0 fps sample rate...
[local] detected 127 face instances across sampled frames
[local] found 3 distinct identities:
  person_00  appears in 58 sampled frames  preview: previews/person_00.jpg
  person_01  appears in 44 sampled frames  preview: previews/person_01.jpg
  person_02  appears in 25 sampled frames  preview: previews/person_02.jpg

Open the preview thumbnails in the previews folder to see who is who.
Pick identity to replace [0-2, default 0]: 1

[local] will replace person_01
[local] scanning source photo folder: /path/to/new_person_photos/
[local] best source photo: .../new_person_photos/portrait_3.jpg
[preprocess] downscaling 3840x2160 -> height 1080...
[preprocess] using downscaled copy: tmp/input_1080p.mp4
[cloud] uploading source image: .../portrait_3.jpg
[cloud] uploading target video: tmp/input_1080p.mp4
[cloud] submitting job to fal…
[cloud] processing frame 120/1558
...
[cloud] downloading result to /path/to/output.mp4

Done. Output: /abs/path/output.mp4
```

### 常用参数

| 参数 | 默认 | 说明 |
| ---- | ---- | ---- |
| `-t / --target` | — | 要编辑的目标视频 |
| `-s / --source-folder` | — | 参考照片文件夹(新人物) |
| `-o / --output` | — | 输出视频路径 |
| `--max-height` | `1080` | 上传前缩放的最大高度;设 `0` 关闭。同时会保证任一边 ≤1920(Pixverse 硬限) |
| `--resolution` | 自动 | 云端输出分辨率:`360p` / `540p` / `720p`(Pixverse 不再支持 1080p) |
| `--mode` | `person` | Pixverse 换脸模式:`person` / `object` / `background` |
| `--keep-audio` / `--no-audio` | keep | 是否保留原视频音轨 |
| `--sample-fps` | `1.0` | 本地扫描每秒采样帧数 |
| `--similarity` | `0.45` | 身份聚类余弦相似度阈值 |
| `--yes` | off | 不交互,自动选最常出现的身份 |
| `--dry-run` | off | 只本地扫描不调云端 |
| `--cpu` | off | 本地推理强制用 CPU |
| `--det-size` | `640` | 检测器输入尺寸 |

### Dry run(只本地扫描)

```bash
python main.py -t in.mp4 -s photos/ -o out.mp4 --dry-run
```

运行完后打开 `previews/` 看每个人长啥样,不会触发云端调用、不收费。

---

## 关于 fal 端点

使用的是 [`fal-ai/pixverse/swap`](https://fal.ai/models/fal-ai/pixverse/swap)。

- **输入**: `video_url` + `image_url` + `mode`(+ 可选 `resolution`
  / `original_sound_switch` / `keyframe_id`)
- **分辨率硬上限**: **任一边不能超过 1920** —— 所以 `ensure_max_height`
  同时按高和宽两个约束缩放,确保 4K / 宽银幕素材也能被接受
- **输出分辨率**: `360p` / `540p` / `720p`(Pixverse 已不再接受 1080p)
- **mode**: `person` / `object` / `background`;`person` 下会重绘面部
  及周边(可能导致长视频中服饰出现漂移)
- **视频格式**: mp4 / mov / webm / mkv

### 已知局限(当前方案)

- **服饰/背景漂移**:Pixverse `person` 模式会在关键帧之间重绘脸部附近
  的像素,长视频中前后半段衣服颜色可能不一致。目前接受这个限制。
- **半月端点不可用**:`half-moon-ai/ai-face-swap/faceswapvideo`
  (face-only、保留衣服)在 fal 上返回 "Application not found",
  暂时没法走这条路。
- **输出最高 720p**:要更高清就本地再做超分(Real-ESRGAN / Topaz)。

> 该端点替换视频里出现的主要人脸。本工具的本地识别 + 选人步骤主要是给
> 你看清视频里都有谁、确认要换的是哪个;当 fal 日后给出按 identity
> 定位的参数时,只改 `fal_api.py` 即可。

---

## 目录结构

```
yovus/
├── face_swap/
│   ├── __init__.py
│   ├── detector.py     # InsightFace 封装:检测 + embedding
│   ├── identity.py     # 贪心聚类成 person_N
│   ├── video.py        # 采样扫描 + ffmpeg 1080p 缩放
│   ├── source.py       # 参考照片文件夹挑最佳
│   ├── fal_api.py      # fal.ai 视频换脸 API 包装
│   └── cli.py          # 交互式 CLI 入口
├── main.py             # 等价于 python -m face_swap.cli
├── requirements.txt
└── README.md
```

---

## 合规提醒

仅用于合法授权的内容。不要用来制作未经当事人同意的深度伪造,不要用来欺诈、
诽谤或冒充他人。遵守你所在地区法律和 fal.ai 的使用条款。
