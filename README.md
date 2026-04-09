# yovus — Hybrid Video Face Swap

本地识别 + fal.ai 云端换脸。流程:

1. 用 **InsightFace** 在本地扫描目标视频,识别视频中出现的所有人物
2. 把人物聚类成"person_00 / person_01 / ..."并输出预览缩略图,你选要换的那个
3. 从你给的**参考照片文件夹**里自动挑一张正脸、清晰度最高的当 source
4. 如果视频分辨率高于 1080p(比如 4K),**本地 ffmpeg 先缩成 1080p**再上传
5. 调用 **fal.ai `half-moon-ai/ai-face-swap/faceswapvideo`** 端点执行换脸
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

```bash
python main.py \
    --target /path/to/input.mp4 \
    --source-folder /path/to/new_person_photos/ \
    --output /path/to/output.mp4
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
| `--max-height` | `1080` | 上传前缩放的最大高度;设 `0` 关闭 |
| `--sample-fps` | `1.0` | 本地扫描每秒采样帧数 |
| `--similarity` | `0.45` | 身份聚类余弦相似度阈值 |
| `--occlusion` | off | 启用遮挡感知(fal 2× 费用) |
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

使用的是 [`half-moon-ai/ai-face-swap/faceswapvideo`](https://fal.ai/models/half-moon-ai/ai-face-swap/faceswapvideo/api)。

- **输入**: `source_face_url` + `target_video_url`(+ 可选 `occlusion`)
- **视频时长上限**: 25 分钟(超出会被截断)
- **FPS 上限**: 25
- **视频格式**: avi, m4v, mkv, mp4, mpeg, mov, mxf, webm, wmv
- **图片格式**: bmp, jpeg, png, tiff, webp

> 注意:该端点在视频中会替换主要出现的那个人脸。本工具的本地识别 + 选人
> 步骤主要是给你看清视频里都有谁、确认要换的是哪个,并给下一版做预留
> (如果 fal 日后提供按 identity 定位的参数,只改 `fal_api.py` 即可)。

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
