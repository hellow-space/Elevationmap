# 启动真实点云高程图

本说明用于进入现有 Docker 容器，加载 ROS 2 Humble 和工作空间环境，然后启动无神经网络的 raw 高程建图。

当前接口：

- 输入：`/cloud_registered`（`sensor_msgs/msg/PointCloud2`，当前真实数据的 frame 为 `camera_init`）
- 输出：`/elevation_mapping_node/elevation_map`（`grid_map_msgs/msg/GridMap`）
- 输出层：`elevation`、`variance`
- 地图 frame：`camera_init`
- 机器人 frame：`base_link`

## 1. 在宿主机查找容器

以下命令在宿主机执行，不是在 Docker 容器内执行：

```bash
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

从输出中找到运行本工作空间的容器名称，后续用它替换 `<container_name>`。不要根据本文猜测容器名称。

如果容器处于停止状态，先启动：

```bash
docker start <container_name>
```

进入容器：

```bash
docker exec -it <container_name> bash
```

## 2. 在容器内加载环境

进入容器后执行：

```bash
cd /root/elevation_map
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

确认当前 ROS 环境：

```bash
echo "$ROS_DISTRO"
echo "$ROS_DOMAIN_ID"
echo "$RMW_IMPLEMENTATION"
```

预期分别为：

```text
humble
42
rmw_cyclonedds_cpp
```

## 3. 确认真实点云和 TF

先确认 `/cloud_registered` 有发布器：

```bash
ros2 topic info /cloud_registered -v
```

确认点云 frame：

```bash
ros2 topic echo /cloud_registered \
  sensor_msgs/msg/PointCloud2 --once --field header
```

当前系统应看到：

```yaml
frame_id: camera_init
```

确认机器人位姿 TF 可用：

```bash
ros2 run tf2_ros tf2_echo camera_init base_link
```

看到连续更新的 Translation 和 Rotation 后，按 `Ctrl+C` 停止检查。第一次提示 frame 不存在、随后开始输出变换，通常只是 TF 缓存尚未建立；如果始终没有变换，则不要继续把空地图当作正常结果。

## 4. 启动 raw 高程建图

在已经加载环境的容器终端执行：

```bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py
```

这个入口默认：

- 使用真实 `/cloud_registered`，不会启动测试点云；
- 关闭神经网络 traversability；
- 发布 `elevation` 和 `variance`；
- 使用 `camera_init` 作为 GridMap frame；
- 使用 `base_link` 更新滚动地图中心；
- 不启动容器内 RViz。

保持该终端运行。需要停止建图时，在这个终端按 `Ctrl+C`。

## 5. 在第二个终端检查高程图

在宿主机另开一个终端，再进入同一个容器：

```bash
docker exec -it <container_name> bash
```

重新加载环境：

```bash
cd /root/elevation_map
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

检查 publisher、消息类型和 QoS：

```bash
ros2 topic info /elevation_mapping_node/elevation_map -v
```

检查消息 frame：

```bash
ros2 topic echo /elevation_mapping_node/elevation_map \
  grid_map_msgs/msg/GridMap --once --field header
```

检查数据层：

```bash
ros2 topic echo /elevation_mapping_node/elevation_map \
  grid_map_msgs/msg/GridMap --once --field layers
```

预期数据层：

```yaml
- elevation
- variance
```

也可以运行仓库中的检查脚本，查看有效格数量、高度范围和方差范围：

```bash
python3 src/terrain_test/check_raw_elevation.py
```

## 6. 从宿主机一条命令直接启动

已经知道容器名称且容器正在运行时，也可以在宿主机直接执行：

```bash
docker exec -it <container_name> bash -lc '
  cd /root/elevation_map
  source /opt/ros/humble/setup.bash
  source install/setup.bash
  export ROS_DOMAIN_ID=42
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  exec ros2 launch elevation_mapping_cupy raw_elevation.launch.py
'
```

`Ctrl+C` 会停止这次 launch。不要在真实 `/cloud_registered` 正在运行时添加 `publish_test_cloud:=true`，以免测试数据和真实数据使用同一输入话题或 TF。

## 常见问题

### 有 topic 但收不到高程消息

依次检查：

1. `/cloud_registered` 是否有 publisher；
2. 点云 `header.frame_id` 是否为 `camera_init`；
3. `camera_init → base_link` TF 是否连续可用；
4. 两个终端的 `ROS_DOMAIN_ID` 和 `RMW_IMPLEMENTATION` 是否一致；
5. 建图节点日志是否报告 TF 不可用。

### 在 Nav2 中使用

当前 elevation bridge 不自动转换 GridMap 与 costmap 的 frame。接入 local costmap 时应保持：

```yaml
global_frame: camera_init
robot_base_frame: base_link
```

本说明只启动和检查高程建图，不启动 Nav2、MPPI 或 RViz。
