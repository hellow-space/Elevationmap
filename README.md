# 四轮足机器人地形评估

本仓库聚焦 Elevation Map 的 2.5D 地形几何特征、可通行性/地形代价，以及后续的 MPPI 局部规划。当前研究对象包括普通障碍物、斜坡、楼梯、平地和粗糙地面；不扩展到完整 3D planner、全局规划、拓扑规划或学习式 traversability，也不直接修改 MPPI。

## 环境与模块

- ROS 2 Humble。
- `src/elevation_mapping_cupy/`：GPU 高程地图融合；raw 模式跳过神经网络推理，发布 `elevation` 和 `variance`。
- `src/elevation_nav2_bridge/`：将 GridMap 接入 Nav2 costmap。
- `src/terrain_test/`：几何指标和高程地图测试工具。测试夹具不代表真实传感器建图结果。

先阅读 [PROJECT_STATUS.md](PROJECT_STATUS.md) 查看进度和实测边界，再看 [EXPERIENCES.md](EXPERIENCES.md) 中与任务相关的已验证经验。真实点云 raw 模式的容器命令见 [RUN_RAW_ELEVATION.md](RUN_RAW_ELEVATION.md)。

## 分支说明

| 分支 | 定位 | 具体内容 |
| --- | --- | --- |
| `main` | 倾斜 frame 问题的诊断基线 | raw 地图默认使用 `camera_init`；诊断记录发现其相对重力方向约倾斜 34°，且与 Nav2 local costmap 的 `map` frame 不一致。 |
| `fix/cloud-sensor-origin`（当前） | 注册点云传感器原点及 raw 地图 frame 修复 | 使用物理雷达原点做量程噪声和射线融合；raw 地图默认使用重力对齐的 `map` frame；GridMap 消息发布实际量化后的滚动栅格中心。 |

## 本分支修复说明

### 注册点云与物理传感器原点

`/cloud_registered` 的点可以位于固定世界坐标系中，不能把 cloud message 的 frame 原点直接当作当前雷达位置。点云订阅配置中的 `sensor_frame` 指物理传感器原点（默认 `livox_frame`），与 cloud frame、机器人 `base_link` 和 GridMap frame 各自独立。TF 只接受精确观测时刻变换，或满足 `max_tf_age` 限制的最新变换；缺失/过期 TF 的帧会被丢弃。

### 重力对齐的 raw 高程图

raw launch 默认使用 `/cloud_registered`，GridMap frame 为 `map`，机器人 frame 为 `base_link`，地图层为 `elevation` 和 `variance`。这样与当前 Nav2 local costmap 的 `map` frame 一致。真实传感器需要提供从 `map` 到物理传感器 frame 的 TF。

### 滚动栅格中心

节点先按整格移动地图，再发布 GridMap。消息 pose 使用实际滚动后的格中心，避免把连续的机器人位置误当作栅格中心。该修复保证数据和消息位置对应；它本身不判断 RViz 中的菱形外观，也不代表已经完成实机导航验证。

## 启动

确保 Humble 工作空间已经构建、真实 `/cloud_registered` 和所需 TF 正在发布，然后运行：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py
```

宿主机通过现有 Docker 容器启动的完整命令见 [RUN_RAW_ELEVATION.md](RUN_RAW_ELEVATION.md)。没有真实输入时不要把测试点云结果写成实机验证。

## 验证与边界

- 本分支的 build、定向测试、隔离 ROS/GPU 链路和数值对比证据见 [PROJECT_STATUS.md](PROJECT_STATUS.md)、[docs/SENSOR_ORIGIN_FIX.md](docs/SENSOR_ORIGIN_FIX.md) 及 `docs/analysis/sensor_origin_2026-11-04/`。
- 记录的验证包括物理传感器原点移动、TF 拒绝帧不刷新观测时间、真实 GPU 融合，以及滚动格中心随整格移动的变化。
- 完整 `colcon test` 有部分默认神经模式测试因环境缺少 `libcudss.so.0` 而失败；不能将整包测试描述为全部通过。
- 尚未用新的实机录包验证高程质量、导航稳定性或端到端延迟。已知外参误差、上游时间戳问题和传感器数据质量仍需单独核查。
- 本分支未实现 terrain critic，也未改动 MPPI。
