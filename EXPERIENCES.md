## 从 Docker 容器通过 SSH 打开主机 RViz2

**日期：** 2026-09-06
**相关模块：** Docker / SSH / ROS 2 Humble / RViz2

**现象：**
容器内执行 `ros2 run rviz2 rviz2` 报 `Package 'rviz2' not found`，但主机已安装 RViz2。容器有 `DISPLAY=:1` 和 X11 socket，也不能直接执行主机程序；在容器 Shell 执行 `exit` 不会得到主机 Shell。

**原因：**
容器和主机的程序安装环境不同。显示接口用于显示窗口，不提供主机命令执行能力。

**解决方法：**
通过 SSH 在主机执行 RViz2，点云与建图仍在容器运行。本次验证的主机用户为 `nvidia`、地址为 `172.26.59.240`、SSH 端口为 `22`、桌面为 `:0`。地址和桌面号变化时需重新确认。

容器专用私钥路径为 `/root/.ssh/elevation_host_rviz`，公钥已加入主机 `~/.ssh/authorized_keys`。私钥不进入仓库。新建容器时需重新配置或安全恢复密钥；只生成不存在的密钥，不覆盖已有密钥：

```bash
ssh-keygen -t ed25519 -f /root/.ssh/elevation_host_rviz -N '' -C elevation-container-rviz
cat /root/.ssh/elevation_host_rviz.pub
```

将公钥整行追加到主机 `~/.ssh/authorized_keys`，主机 `.ssh` 目录权限为 `700`，`authorized_keys` 为 `600`。曾因粘贴的 heredoc 结束标记 `EOF` 前有空格，终端一直显示 `>`，公钥未完成写入；按 Ctrl+C 后用 `printf '%s\n' '公钥整行' >> ~/.ssh/authorized_keys` 完成授权。不要发送私钥或密码。

以下是已实际执行的打开与自动关闭命令（在容器执行）。结束标记 `HOST_SCRIPT` 必须顶格：

```bash
ssh -i /root/.ssh/elevation_host_rviz \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/tmp/elevation-map-host-known-hosts \
  nvidia@172.26.59.240 'bash -s' <<'HOST_SCRIPT'
source /opt/ros/humble/setup.bash
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)
rviz_log=$(mktemp /tmp/elevation-rviz-test.XXXXXX.log)
printf 'RViz log: %s\n' "$rviz_log"
timeout --signal=INT --kill-after=3s 7s ros2 run rviz2 rviz2 >"$rviz_log" 2>&1
rviz_result=$?
printf 'Launch exit status: %s\n' "$rviz_result"
cat "$rviz_log"
HOST_SCRIPT
```

上述 known-hosts 文件在首次连接时通过 `StrictHostKeyChecking=accept-new` 创建。它位于 `/tmp`，清理后需要重新确认主机指纹并登记，不能假设永久存在。

**验证：**
SSH 返回主机名 `nvidia-desktop`；RViz 日志出现 `OpenGl version: 4.6 (GLSL 4.6)`，确认初始化成功。约 7 秒后发送 SIGINT，等待 3 秒仍未退出，由 timeout 强制终止，退出码为 `137`。随后检查主机进程，没有残留 RViz2。本次验证的是启动与关闭，没有验证地图订阅或截图内容。

**适用范围：**
容器可访问主机 SSH、密钥已授权、主机 Humble/RViz2 和桌面会话可用。本次显示授权已经可用，没有额外修改 X11 授权。

**避免：**
不要把容器 `DISPLAY` 当作主机命令入口；不要将认证失败误判为网络不通；不要用 `pkill rviz2` 关闭用户原有窗口。上述 timeout 仅管理本次启动的进程组。

## 局部平面拟合的坐标、误差和最小验证入口

**日期：** 2026-09-06
**相关模块：** convex_plane_decomposition / terrain_test

**现象：**
完整平面分割目录存在 `COLCON_IGNORE`，而需要先验证局部 slope/roughness；原函数为私有方法，完整包依赖 grid_map、OpenCV 和 CGAL。

**原因：**
局部数值函数自身仅依赖 Eigen、窗口尺寸和分辨率。原函数的误差返回值是最小协方差特征值（距离均方值 m²），不是 roughness RMS；矩阵坐标采用行沿负 X、列沿负 Y。

**解决方法：**
`src/terrain_test/geometry_validation/validate_geometry.py` 从原源码提取两个完整函数定义，编译最小测试适配器；不复制一份手写算法、不改原代码或启用整个目录。roughness 取有效误差的平方根，坡度由法向量换算，并单独比较法向量方向。

**验证：**
运行脚本加 `--mutation-check`：17 组通过，零粗糙度输出、X 反向、X 分辨率翻倍三种故障全部检出。10/20 mm 非零 roughness 使用周期 q=(1,-2,1) 的外积构造，独立解析真值见同目录 README；JSON 快照保存源码校验和及误差。

**适用范围：**
仅验证这两个数值函数，不能替代完整 GridMap 遍历、生产类初始化或融合链路验证。提取器不是通用 C++ 解析器，原函数结构变化时需要复核生成源码。

**避免：**
不要用角度大小测试代替法向量方向测试；不要将不足三个有效点或共线输入的 `1e30` 无效哨兵解释为平地。不要把高程标准差当作正交平面 RMS。已验证的 15° 基础坡面加竖直起伏样本，其最佳拟合角约 15.84248°，并非求解器数值错误；应区分基础地形角度和拟合指标真值。

## 容器 GridMap 在主机 RViz 的实收与显示验证

**日期：** 2026-09-06
**相关模块：** terrain_test / grid_map_msgs / grid_map_rviz_plugin / DDS

**现象：**
需要在主机查看容器计算的 slope/roughness，单独成功打开 RViz 不能证明数据已到达。

**原因：**
两端必须使用可通信的 ROS 环境，GridMap 布局、指标单位和颜色范围也必须一致。

**解决方法：**
本次验证两端使用 Humble、`ROS_DOMAIN_ID=42`、`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`。主机已有 GridMap 插件。矩阵使用 column-major，维度标签为 column_index/row_index，stride 分别为 rows*cols/rows，零缓冲起始索引；length_x=rows*r、length_y=cols*r，与原平面函数的负X/负Y索引约定一致。

**验证：**
`test_geometry_demo.py` 的非方阵序列化、指标与 NaN 测试3项通过。主机 `check_demo_topics.py` 实际收到三个 GridMap 并逐格核对3层。RViz 截图确认3幅图与标签，Global Status OK。脚本和配置在 `src/terrain_test/geometry_validation/`。

**适用范围：**
当前为静态数学地形显示，三个图的 Y 偏移仅用于并排比较。主机配置和核验脚本曾复制到 `/tmp`，清理后需从仓库重新复制。

**避免：**
不要只看启动日志就声称地图显示成功。不要自动缩放每幅图的颜色而失去指标对比：本例 slope 固定0–20°、roughness 固定0–0.02 m，蓝低红高。只计算完整3×3窗口，边界/缺失/退化拟合保留 NaN，不填零。

## raw 高程模式必须跳过推理，不能只隐藏输出层

**日期：** 2026-09-07
**相关模块：** elevation_mapping_cupy

**现象：**
用户只需高度和不确定度。旧代码即使不发布 traversability，也会加载权重并每帧推理；use_chainer=false只是改用Torch。

**原因：**
权重初始化与推理不受发布配置控制；漂移补偿依赖可通行性分数，而点计数/法向量相关 GPU 计算还有几何融合用途。

**解决方法：**
新增 enable_traversability 开关，false时跳过权重/后端/推理并保护漂移补偿；raw launch 使用空插件配置、关闭启动初始化，只发布elevation和variance。仍保留必要CuPy几何运算，不能把CUDA等同于神经网络。

**验证：**
真实GPU回归在权重文件不存在时成功融合，未新增Torch/Chainer模块；重复观测高度误差收敛且方差下降。对漂移guard做内存故障注入能检出错误；colcon目标测试通过。主机实收2层并显示raw地形，复现见 src/terrain_test/RAW_ELEVATION.md。

**适用范围：**
variance为高度估计方差m²，需结合有效高程格使用；不是roughness或真实误差保证。关闭模式的可通行性查询不能用于通行判断。

**避免：**
不要删掉error_counting_kernel等看似与可通行性有关的核函数，它还更新融合所需点计数。不要期待有限先验下三帧融合就与数学平面完全重合，应测收敛与方差变化。不要把同名raw理解为关闭所有测量过滤/可见性清理。
