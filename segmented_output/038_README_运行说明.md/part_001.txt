# 一镜到底战场白膜预演 V1.2 — Blender 执行包

## 内容
- `Battlefield_OneTake_Previs_V1_2.py`：完整场景生成脚本，目标 Blender 5.2.x。
- `terrain_reference.png`：本轮确认的连续山地、森林、河流地貌视觉基准，脚本会尝试打包进 .blend。
- `storyboard_*.png`：五组故事板参考。
- `Battlefield_OneTake_Previs_V1_2_CameraRoute_TopView.png`：全战场摄影机俯视路线。
- `Battlefield_OneTake_Previs_V1_2_CameraRoute_Detail.png`：森林、山沟、破屋、河流区域的转弯/穿越细节。
- `Battlefield_OneTake_Previs_V1_2_CameraHeightProfile.png`：摄影机高度剖面图。

## Windows / Blender 执行
1. 解压整个文件夹，保持脚本与 `terrain_reference.png` 在同一目录。
2. 打开 Blender 5.2.x，进入 Scripting 工作区。
3. Open 打开 `Battlefield_OneTake_Previs_V1_2.py`。
4. 点击 Run Script。
5. 脚本完成后，会在脚本同目录尝试保存 `Battlefield_OneTake_Previs_V1_2.blend`，并在 Blender Text 数据块中生成 `BFP_V12_BUILD_REPORT`。
6. 播放帧 1—900。建议先用实时视口检查，不必先渲染完整 30 秒。

## 本版重点
- 相机路线改为多段 S 曲线、急转弯、俯冲、横向闪避、光轴滚转和实体框架穿越。
- 开场高度提高至约 150m，最终升空约 145m。
- 四架轰炸机两侧错位迎面接近；鸽子从左侧前景滑翔出画；四枚航空炸弹分批释放并分阶段下坠。
- 地形改为连续程序化山地网格，周边山脊扩大；河道扩展为约 72m 宽的白膜河面。
- 增加森林倒木救援、树木框架、梧桐沟门口背人/木杆光荣弹拉环、日军环绕、爆炸碎片、河面浮尸和渡河群演。
- 所有场景事件共用 1—900 帧主时间轴，摄影机只负责观察，不控制事件启动。

## 重要限制
当前交付环境没有安装 Blender 可执行程序或 `bpy` 模块，因此本次完成了 Python 语法检查与结构静态检查，未在此环境生成或播放 `.blend`。实际相机碰撞、人物落地贴合、镜头遮挡、爆炸穿越效果和渲染性能必须在本机 Blender 中验收。

## 版本与回滚
V1.2 是独立新版本，不覆盖 V1.1。脚本会隐藏 V1.1 生成集合，保留其对象与历史版本供回滚；重复运行 V1.2 时仅清理本版生成集合。
