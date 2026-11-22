# 启动真实点云高程图

在宿主机终端直接执行：

```bash
docker start elevation_env >/dev/null
docker exec -it elevation_env bash -lc '
cd /root/elevation_map &&
source /opt/ros/humble/setup.bash &&
source install/setup.bash &&
export ROS_DOMAIN_ID=42 &&
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp &&
exec ros2 launch elevation_mapping_cupy raw_elevation.launch.py
'
```

按 `Ctrl+C` 停止。

当前配置使用：

- 输入：`/cloud_registered`
- 输出：`/elevation_mapping_node/elevation_map`
- GridMap frame：`map`
- 数据层：`elevation`、`variance`
