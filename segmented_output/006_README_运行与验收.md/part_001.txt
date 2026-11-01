# 一镜到底战场白膜预演 · V2

本版以用户《Blender完整实现需求表 V1.0》为执行基线，继承附件 V1.2 的程序资产并重排镜头与事件。原 ZIP 和 `reference_original/` 均保留，未覆盖原稿。

交付视频：`battlefield_v2_previs.mp4`，480×270，H.264，30 FPS，5,701 帧，190.033 秒。包含老孟 OS 字幕，无配音或音效。源工程默认画幅为 640×360，可自行提高后重渲染。

阶段时间：0–30 秒高空；30–59 秒森林；59–79 秒李行沟；79–103 秒破屋；103–133 秒河流；133–146 秒交接；146–167 秒老孟；167–190 秒山谷。

## 打开工程

打开 `battlefield_v2.blend`，按小键盘 0 进入活动摄影机，空格播放。30 FPS，1–5701 帧，约 190 秒。群演和事件为可寻帧的关键帧轨道，无须点击镜头触发。实时播放速度取决于硬件；视频是按 30 FPS 输出的离线预演。

实际生成与检查环境：Blender **4.3.2**。用户指定的 **5.2.x 尚未实测**。工程不是“5.2 已验收版本”。请保留此工程后，在 5.2 中另存并重新运行验证，不要覆盖历史文件。

## 一键重建

保留本文件夹内 Python 文件的相对位置。从新的 Blender General 文件运行：

```bash
blender -b -t 8 --python battlefield_v2.py
```

也可在 Blender Scripting 中打开该主脚本执行，建议首先保存到本交付目录。主脚本构建后调用同目录 `validate_scene.py`，自动修正地形、采样避障、烘焙摄影机并输出检查报告。任何 Python 异常都应视为构建失败；以日志最后的 `VALIDATION_DONE` 和报告为准。不要把早期 `V2_BUILD_SUCCESS` 当成最终验证通过。

不要在原 V1.2 场景中直接混合执行本脚本。旧版文件作为独立历史版本保留。同一 V2 场景重复执行会清理本版集合内对象，再重新构建；不会叠加本版人物和环境。

## 调整

主脚本末段 `CFG` 为帧率、摄影机安全半径、余量、画幅、浮尸数、河岸人数、随机种子及各阶段时长配置。`V2_KEYS` 为观察位置、目标位置、滚转和画面意图。`time_map` 把旧事件时钟转换为新 Master Timeline；修改时应保持两列严格递增。修改摄影机或动态障碍后，应重新生成报告和视频。

河中主要群演在 `build_storyboard_details()` 的人群循环；原有关键人物在 `build_characters_and_props()`；`extra_events()` 增补动作与人数。集合前缀 `BFP_V20_*` 按地形、树林、山沟、房屋、河流、人物、道具、效果和摄影机分类。重复人物共享低多边形网格，角色姿态和物体变换独立。效果是白膜几何代理，没有流体/烟雾物理仿真。

摄影机碰撞体：半径 0.22m + 0.12m 安全余量。固体按实际三角网格检测，动态部分按所在帧求值；烟云、弹道光迹、水花与水面等光学效果不作为实体墙。路线修正后烘焙为位置、姿态关键帧，可独立编辑。线性烘焙保证位置连续，但没有保证加速度连续；速度图应参与人工审查。

## 输出与复现

```bash
# 重新输出关键画面
blender -b battlefield_v2.blend -t 8 --python render_previs.py -- checkpoints
# 输出本交付快速预演的 480×270 帧序列
blender -b battlefield_v2.blend -t 4 --python render_fast.py -- 1 5701
# 按工程默认画幅输出完整帧序列（耗时）
blender -b battlefield_v2.blend -t 8 --python render_previs.py -- full
# 用所有真实渲染帧编码；不通过重复关键帧伪造连续动画
ffmpeg -framerate 30 -start_number 1 -i frames/frame_%04d.png -vf "subtitles=old_meng_os.srt" -c:v libx264 -crf 20 -pix_fmt yuv420p -y battlefield_v2_previs.mp4
# 路线、高度和速度图；系统 Python 需 matplotlib
python plot_camera.py
```

工程包含参考图片数据。若单独拿主脚本重建且希望重新打包参考图，把附件的原始目录保存在交付目录的上一级 `reference_original/Battlefield_OneTake_Previs_V1_2_Package/`。

## 验收范围

`collision_report.json` 记录实际运行版本、静态/动态碰撞体数量、每帧采样、修正记录、残余碰撞与速度极值。此检查不等于连续时间的扫掠体积数学证明，也不能证明镜头里的人物表演可读。

`visibility_report.json` 是关键主体视锥和遮挡的测量证据；一个主体进入视锥不代表完整动作已验收。`验收记录.md` 另列视觉观察及尚未达到的要求。老孟 OS 目前以字幕交付，没有配音和战场音效。

地貌为参考图指导的程序化近似布局，不是对图像进行测绘重建。整体风格保持几何白膜，不能将故事板中的真人、烟火细节理解为已实现的最终美术品质。
