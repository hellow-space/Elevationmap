# 四轮足机器人地形评估

本仓库聚焦 Elevation Map 的 2.5D 地形几何特征、可通行性/地形代价，以及后续的 MPPI 局部规划。目标地形包括平地、斜坡、楼梯、普通障碍物和粗糙地面。当前不扩展到完整 3D planner、全局规划、拓扑规划或学习式 traversability，也不直接修改 MPPI。

## 环境与模块

- ROS 2 Humble。
- `src/elevation_mapping_cupy/`：GPU 高程地图融合。raw 模式跳过神经网络推理，发布 `elevation` 和 `variance`。
- `src/elevation_nav2_bridge/`：将 GridMap 接入 Nav2 costmap。
- `src/terrain_test/`：几何指标和高程地图测试工具。测试夹具结果不代表真实传感器建图结果。

先阅读 [PROJECT_STATUS.md](PROJECT_STATUS.md) 查看当前进度和验证边界，再看 [EXPERIENCES.md](EXPERIENCES.md) 中与任务相关的已验证经验。真实点云 raw 模式的容器启动命令见 [RUN_RAW_ELEVATION.md](RUN_RAW_ELEVATION.md)。

## 分支说明

| 分支 | 定位 | 说明 |
| --- | --- | --- |
| `main`（当前） | 集成后的工作分支 | 已包含 `fix/cloud-sensor-origin` 的传感器原点、重力对齐地图 frame 和滚动栅格中心修复。raw 默认 GridMap frame 为 `map`。 |
| `fix/cloud-sensor-origin` | 修复来源分支 | 保留修复工作的独立历史和分支专用 README；其代码提交已合入 `main`。 |

## 当前 raw 高程入口

默认使用 `/cloud_registered` 输入，物理传感器 frame 为 `livox_frame`，GridMap frame 为 `map`，机器人 frame 为 `base_link`，输出层为 `elevation` 和 `variance`。配置入口见 `src/elevation_mapping_cupy/elevation_mapping_cupy/config/setups/raw/elevation.yaml` 和 raw launch。真实数据运行需要对应的 TF 链路。

已构建工作空间时，运行：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py
```

没有真实点云时，不要把测试点云的结果描述成实机验证。

## 已合入的修复

### 物理传感器原点

注册点云可以处于固定世界坐标系，不能将点云消息 frame 的原点直接当成当前雷达位置。`sensor_frame` 单独指定物理传感器原点，默认 `livox_frame`；它与 cloud frame、`base_link` 和 GridMap frame 各自独立。点云融合的量程噪声和可见性射线使用传感器相对坐标。TF 优先使用观测时刻变换；最新变换仅在 `max_tf_age` 范围内回退，缺失或过期时丢弃该帧。

### 重力对齐地图与滚动中心

raw 地图发布在与 Nav2 local costmap 一致的重力对齐 `map` frame。滚动地图按整格移动，GridMap pose 现在发布实际量化后的格中心，不再使用连续机器人位置。地图仍是 2.5D elevation 表面，pose 的高度为零，绝对高度保存在 elevation 层。

## 验证和限制

- 传感器原点修复的 build、定向测试、隔离 ROS/GPU 链路和数据对比见 [docs/SENSOR_ORIGIN_FIX.md](docs/SENSOR_ORIGIN_FIX.md) 与 `docs/analysis/sensor_origin_2026-11-04/`。
- 滚动中心修复的测试和 GPU/ROS 验证记录见 [PROJECT_STATUS.md](PROJECT_STATUS.md)。这些记录不是本次 merge 后新运行的实验。
- 已有完整 `colcon test` 曾因环境缺少 `libcudss.so.0`，使默认神经模式相关测试失败；不能描述为整包全通过。
- 尚未用新的实机录包验证高程质量、导航稳定性或端到端延迟。外参精度、上游时间戳和传感器数据质量仍需单独核查。
- 尚未实现 terrain critic，也未将几何指标接入 MPPI rollout evaluation。
