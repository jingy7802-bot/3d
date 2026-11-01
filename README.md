# 一镜到底战场白膜预演 V2 · 文件交付

本仓库为用户指定的公开交付仓库。原始文件保留；当前为 V2 实现稿，**不是最终验收通过版本**。

## 下载和查看

只看预演：下载 `.mp4` 后用播放器打开。在 Blender 中打开现成场景：下载 `.blend`，选择“文件 → 打开”，不是“文件 → 导入”；无需拼接或运行脚本。

- [下载 V2 文件包（约 45 MB）](https://raw.githubusercontent.com/jingy7802-bot/3d/main/Battlefield_Previs_V2_Implementation.zip)
- [下载/播放预演视频（480×270，30 FPS，190.033 秒）](https://raw.githubusercontent.com/jingy7802-bot/3d/main/delivery_v2/battlefield_v2_previs.mp4)
- [下载可编辑 Blender 工程](https://raw.githubusercontent.com/jingy7802-bot/3d/main/delivery_v2/battlefield_v2.blend)
- [查看完整画面索引](https://github.com/jingy7802-bot/3d/blob/main/delivery_v2/contact_sheet.jpg)
- [操作与重建说明](https://github.com/jingy7802-bot/3d/blob/main/delivery_v2/README_%E8%BF%90%E8%A1%8C%E4%B8%8E%E9%AA%8C%E6%94%B6.md)
- [验收记录与未完成项](https://github.com/jingy7802-bot/3d/blob/main/delivery_v2/%E9%AA%8C%E6%94%B6%E8%AE%B0%E5%BD%95.md)

点击上述文件后，可使用 GitHub 的 **Download raw file / 下载原始文件**。不要下载整个仓库来代替 45 MB 交付包：仓库还保留了约 986 MB 的全部逐帧图片、旧渲染检查图和备份工程。

## 完整文本分段

- [全部分段索引（逐文件、逐段、行号、校验值）](https://github.com/jingy7802-bot/3d/blob/main/segmented_output/INDEX.md)
- [文本分段打包下载](https://raw.githubusercontent.com/jingy7802-bot/3d/main/segmented_output/all_text_segments.zip)
- [完整产物清单](https://github.com/jingy7802-bot/3d/blob/main/DELIVERY_MANIFEST.json)

文本按每 96 行原样分段；没有省略号代替代码，没有只给关键函数。分段是原文切片，不是能单独运行的脚本。目录内附 `reassemble.py`，可把所有分段按清单恢复成原始文件并检查 SHA-256。

## 文件位置

| 内容 | 路径 |
|---|---|
| 主脚本 | `delivery_v2/battlefield_v2.py` |
| 碰撞、贴地与摄影机检查脚本 | `delivery_v2/validate_scene.py` |
| 其他渲染、绘图和审计脚本 | `delivery_v2/*.py` |
| Blender 完整工程与备份 | `delivery_v2/battlefield_v2.blend`、`.blend1` |
| 连续预演视频 | `delivery_v2/battlefield_v2_previs.mp4` |
| 全部 5,701 张真实渲染帧 | [逐帧分页索引](https://github.com/jingy7802-bot/3d/blob/main/render_frames_index/INDEX.md)；原图在 `delivery_v2/frames/` |
| 最终代表帧 | `delivery_v2/review_frames/` |
| 较早的检查帧 | `delivery_v2/checkpoints/` |
| 俯视路线、高度和速度曲线 | `delivery_v2/camera_*.png` |
| 逐帧摄影机数据、事件轨道 | `delivery_v2/camera_samples.csv`、`event_tracks.csv` |
| 检查结果和运行日志 | `delivery_v2/*.json`、`*.log` |
| 原始附件和参考图 | `reference_original/` |

## 当前边界

实测版本为 Blender 4.3.2；用户指定的 Blender 5.2.x 未实测。摄影机逐帧采样未检出残余碰撞，但不能当成连续扫掠证明或故事板全部验收通过。水下效果、风吹硝烟/阳光变化、部分表演可读性和接触关系仍有未通过项，详见验收记录。视频包含老孟 OS 字幕，没有配音或战场音效。

原始附件、源程序及生成产物均不因本次上传而修改。Python 字节码缓存不是交付内容，不上传。
