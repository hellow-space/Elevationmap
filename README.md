# 四轮足机器人地形评估

本仓库聚焦 Elevation Map 的 2.5D 地形几何特征、可通行性/地形代价，以及后续的 MPPI 局部规划。当前研究对象包括普通障碍物、斜坡、楼梯和平地/粗糙地面；暂不扩展到完整 3D planner、全局规划、拓扑规划或学习式 traversability，也不直接修改 MPPI。

## 环境与模块

- ROS 2 Humble。
- `src/elevation_mapping_cupy/`：GPU 高程地图融合；raw 模式关闭神经网络推理，发布 `elevation` 和 `variance`。
- `src/elevation_nav2_bridge/`：将 GridMap 接入 Nav2 costmap。
- `src/terrain_test/`：几何指标和高程地图测试工具。测试夹具结果不代表真实传感器建图结果。

先阅读 [PROJECT_STATUS.md](PROJECT_STATUS.md) 了解当前进度，再看 [EXPERIENCES.md](EXPERIENCES.md) 中与任务相关的已验证经验。真实点云 raw 模式的容器启动命令见 [RUN_RAW_ELEVATION.md](RUN_RAW_ELEVATION.md)。

## 分支说明

| 分支 | 定位 | 重要说明 |
| --- | --- | --- |
| `main` | 倾斜 frame 问题的诊断基线 | raw 地图默认使用 `camera_init`。诊断记录发现该 frame 相对重力方向约倾斜 34°，且与 Nav2 local costmap 的 `map` frame 不一致；此分支没有包含后续修复。 |
| `fix/cloud-sensor-origin` | 传感器原点与地图 frame 修复 | 在 `main` 后增加物理传感器原点 TF、raw 地图重力对齐 `map` frame，以及滚动栅格中心发布修正。实机新录包和导航效果仍需单独验证。 |

切换分支前查看 `git status`，确认没有尚未保存的修改。两分支的提交差异可用 `git log --oneline main..fix/cloud-sensor-origin` 查看。

## `main` 分支的 raw 入口

在已准备好 Humble 工作空间、真实 `/cloud_registered` 输入及所需 TF 的环境中，执行：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py
```

此分支默认 GridMap frame 为 `camera_init`，输出层为 `elevation`、`variance`。它保留倾斜 frame 诊断时的配置；需要重力对齐 `map` frame 和物理雷达原点处理时，使用 `fix/cloud-sensor-origin` 分支。不要用 `publish_test_cloud` 的测试点云结果代替真实传感器验证。

## 研究边界

- 优先验证 elevation、slope、roughness、step/height difference、surface normal 和 variance 等确定性几何量能否区分目标地形。
- 验证几何指标前不实现 terrain critic，不把现有 traversability 分数当作已适配的机器人通行判据。
- 生产地图几何层、真实点云融合误差和机器人通过条件以 [PROJECT_STATUS.md](PROJECT_STATUS.md) 的实测记录为准。
