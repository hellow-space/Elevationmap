# 只看融合高程与不确定度（无神经网络）

当前实现增加 `enable_traversability` 开关，默认 true 保持旧行为。新 `raw_elevation.launch.py` 将其关闭，真正跳过权重加载、Torch/Chainer 后端初始化和卷积推理。只删除发布 layers 中的 traversability 不会达到这个效果；`use_chainer: false` 也只是切换到 Torch。

## 使用现有点云与 TF

容器终端：

```bash
cd /root/elevation_map
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py
```

默认订阅 `/camera/depth/points`，要求已有从点云 frame 到 `map` 的 TF，和 `map` 到 `base_link` 的机器人位姿。默认不发布测试点云或 TF，也不在容器启动 RViz。

可选参数：`pointcloud_topic:=/你的点云话题`、`map_frame:=odom`、`base_frame:=你的机身坐标系`、`use_sim_time:=true`（仅存在可用 /clock 时）。主机 RViz Fixed Frame 相应修改。

## 没有真实点云时，先用测试输入看效果

```bash
cd /root/elevation_map
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=43
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch elevation_mapping_cupy raw_elevation.launch.py publish_test_cloud:=true
```

测试输入使用仓库现有 synthetic_pointcloud_tf_publisher，机器人静止，关闭动态障碍，发布点云及 map→base_link。不要与发布相同 TF/话题的真实数据源同时使用。本次验证使用独立 Domain 43，主机必须相同；接真实数据时使用其已有 Domain。

## 主机 RViz

将 `src/elevation_mapping_cupy/elevation_mapping_cupy/rviz/raw_elevation.rviz` 复制到主机；本次已复制为 `/tmp/raw_elevation.rviz`。

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=43
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
rviz2 -d /tmp/raw_elevation.rviz
```

- 话题：`/elevation_mapping_node/elevation_map`，消息 GridMap。
- 层：`elevation`（米）、`variance`（平方米）。几何高度始终选择 elevation。
- 默认启用 `Raw elevation (m)`，按高程着色。
- 查看不确定度：关闭 `Raw elevation (m)`，启用 `Variance (m2) - enable to color uncertainty`。颜色取 variance，仍按 elevation 显示起伏。不要同时启用两项，以免表面重叠闪烁。
- 方差色标固定0–0.01 m²，蓝低红高；超出范围颜色饱和，可以手动调整最大值。若想看标准差，数值上为 sqrt(variance)，单位米；当前没有额外发布标准差层。
- 未观测格不应当作已知平地；判断方差时应同时检查 elevation 有效性。variance 是融合模型的高度估计不确定度，不是粗糙度，也不是已经标定过的真实误差保证。

## raw 的边界

这里是融合器原始 elevation/variance，没有插件平滑、补洞、尖峰去除，不是未经融合的原始点云。原来的点云距离/高度过滤、统计融合、可见性清理等仍保留；仍需要 NVIDIA GPU 和 CuPy/CUDA，它们用于几何数值计算，不代表使用神经网络。

raw 配置还关闭启动时的人工平面初始化，以及依赖 traversability 的高度漂移补偿。可通行性请求在关闭状态返回未知（get_traversability 全 NaN），多边形可通行性判断明确报禁用，不能据此作通行决策。纯几何法向量计算仍保留，供现有清理逻辑使用。

## slope / roughness

不需要神经网络：局部平面法向量可换算 slope，点到该平面的距离 RMS 可得到 roughness。此前 `geometry_validation/` 已验证该方法并提供数学地形 RViz 演示，但目前 raw 建图输出尚未接入这两个几何层。不要把那个测试演示当作当前 raw 点云地图的计算结果。

## 本次验证

- `colcon build --packages-select elevation_mapping_cupy --symlink-install` 成功。
- 新增 GPU 回归测试覆盖：缺失权重仍能融合、不加载 Torch/Chainer、重复观测高度收敛且方差下降、禁用可通行性查询、默认模式仍需权重。
- 临时内存修改去掉漂移保护条件后，针对性测试失败（出现非零 additive_mean_error）；原文件未改动，正式回归应通过。
- 主机 Domain43 实际收到 elevation/variance 两层，本次样本5723个有效格子，高度约0–0.397 m，方差约0.000230–0.019185 m²。这是单次消息记录，连续发布时数值会变化。
- 主机实际 RViz 窗口 Global Status OK，显示融合地形；检查脚本为 `src/terrain_test/check_raw_elevation.py`，可复制到主机在同一 Domain 下运行。
