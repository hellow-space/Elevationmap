# 局部平面 slope / roughness 最小精度验证

目的：用数学真值验证仓库现有局部平面拟合数值计算，不需要 Gazebo、ROS 节点、GPU 或传感器。这里的人工高程矩阵仅是测试夹具，不是真实机器人实验。

## 一条命令复现

在 `/root/elevation_map`：

```bash
python3 src/terrain_test/geometry_validation/validate_geometry.py --mutation-check
```

依赖：Python 3 标准库、`g++`（C++17）、`/usr/include/eigen3`。脚本先编译再运行；失败退出非零，不丢弃失败格子。没有改动生产算法，也没有删除 `plane_segmentation/COLCON_IGNORE`。不需要重新编译整个 ROS 工作空间。

生成的可执行文件、提取源码和默认 JSON 报告位于 `build/geometry_validation/`，被 Git 忽略。`--output 路径` 可指定报告位置；已验证的结果快照另保存在本目录 `results_2026-09-06.json`。

## 实际测到了什么

每次构建从 `SlidingWindowPlaneExtractor.cpp` 提取原始 `normalAndErrorFromCovariance` 和 `computeNormalAndErrorForWindow` 两个函数定义，函数体保持不变，生成 `original_fit.inc`。`fit_driver.cpp` 只负责输入输出；测试类壳只提供原函数使用的 `kernel_size` 和 `resolution`。Eigen 矩阵和求解器均为真实实现，没有 mock，也没有用 Python 重写拟合算法。

这验证了这两个数值函数，**不等于**编译运行完整 `SlidingWindowPlaneExtractor` 类、GridMap 窗口遍历、分割、ROS 发布或建图融合。提取器只针对当前两个函数的简单括号结构，不是通用 C++ 解析器；源码变更后需查看生成文件并复核适用性。JSON 保留原文件 SHA-256 和编译器/平台信息。

## 指标定义和真值

- 原算法把有效高程格映射成 `(-row*r, -col*r, height)`，因此行对应负 X、列对应负 Y。测试不仅比较坡角，还检查法向量分量，防止角度正确但方向相反。
- 原算法计算协方差 `E[ppᵀ] - E[p]E[p]ᵀ`，使用最小特征值对应的法向量，并翻转朝上。
- `slope = atan2(sqrt(nx²+ny²), nz)`，转换为度。这是坡度大小，正负坡由法向量方向区分。
- 原函数返回的是垂直于拟合平面的距离 **均方值**，单位 m²；`roughness = sqrt(MSE)`，单位 m。它不是高程方差或最大高度差。
- 少于三个有效点、或共线导致平面不可确定时，原算法返回向上法向量和 `1e30` 误差哨兵。测试检查哨兵，不把它当作平地，也不对其报告有效粗糙度。

### 平面

41×41 矩阵，分辨率 0.05 m，3×3 窗口，跳过边界后 39×39=1521 个窗口。采用 `h=gx*x+gy*y+offset`，解析法向量为 `(-gx,-gy,1)` 归一化，粗糙度真值为 0。

覆盖水平、X/Y 方向 ±15°、合成对角方向 15°；附加 10 m 高度平移、0.1 m 分辨率和 5×5 窗口（1369 个窗口）。这些是有限样本，不是所有角度/尺度的精度保证。

### 已知非零 roughness

取周期序列 `q=(1,-2,1)`，高度扰动为 `a*q(row)*q(col)`。任意连续 3×3 窗口的扰动均值与 X/Z、Y/Z 交叉协方差均为 0；竖直方差为 `4a²`，水平两个方向方差为 `v=2r²/3`。

当 `4a² < v` 时最佳拟合平面水平，RMS 真值为 `2a`。测试 `a=0.005 m` 和 `a=0.01 m`，分别对应 **10 mm、20 mm**，因此能发现“永远输出零粗糙度”的错误。

### 带起伏的斜坡

叠加 `gx=tan(15°)` 和上述 10 mm 扰动后，XZ 协方差块为：

```text
[v,       gx*v        ]
[gx*v,    gx²*v + 4a² ]
```

用该 2×2 矩阵的解析特征值/向量作为独立真值。竖直扰动会改变正交最小二乘平面，拟合角度真值约 **15.84248°**，roughness 约 **9.64021 mm**。不能要求这个样本依然输出 15° 或把其差异全部当成数值误差；模型定义与基础地形角度不同。

## 验收和故障注入

执行前规定：每个有效窗口角度绝对误差 <0.1°、roughness 绝对误差 <0.0001 m、法向量最大分量误差 <1e-5。所有输出必须有限，输出数量必须与输入窗口数一致。无效输入单独检查。

`--mutation-check` 在临时文件中分别注入：roughness 恒为零、X 轴符号反转、X 方向分辨率乘二。每种错误必须造成至少一组失败；不改工作树里的原算法。此处新增的是已有算法的特性验证测试，没有新增生产逻辑；故障注入证明测试能检出真实计算错误。

## 结果与下一步

数值结果以 JSON 快照为准。下述测试地形可视化已发布 slope/roughness 层；生产建图节点尚未接入，未验证点云融合、滤波对指标的影响，也未判断机器人能否通过。

## 在主机 RViz 看测试地形

这是上述数学测试地形的可视化，不是传感器建图结果。四块地形：平地、15° 光滑斜坡、RMS 10 mm 和 20 mm 的起伏面。C++ 原函数先计算一次，容器以 2 Hz 重复发布；不需要启动原来的 synthetic_depth_demo，也不会改它的地图话题。

容器终端：

```bash
cd /root/elevation_map
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
python3 src/terrain_test/geometry_validation/geometry_demo.py
```

脚本启动时自动编译现有 C++ 测试适配器，并打印四块地形的平均指标。保持终端运行，Ctrl+C 停止。

将本目录 `geometry_demo.rviz` 复制到主机（本次已放在 `/tmp/geometry_demo.rviz`）。在主机终端执行：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
rviz2 -d /tmp/geometry_demo.rviz
```

容器通过 SSH 启动主机 RViz 的认证与显示配置见根目录 `EXPERIENCES.md`。`/tmp` 配置清理后需重新复制。

默认三个显示均启用，Fixed Frame 为 `map`。每幅图都有相同四块地形，并用高程作为真实显示高度，仅改变颜色来源；发布时将三个图的中心沿 Y 分别移动 +5、0、-5 m，以并排比较，不表示真实地形位置。

| 显示 / 话题 | 颜色层和范围 |
|---|---|
| Height / `/terrain_geometry/elevation` | elevation：−0.3 到 +0.3 m |
| Slope / `/terrain_geometry/slope` | slope：0 到 20° |
| Roughness / `/terrain_geometry/roughness` | roughness：0 到 0.02 m |

蓝色代表范围低端、红色代表高端。默认视角从屏幕左到右是 roughness、slope、height，以图中标题为准。平地和光滑坡的 roughness 应接近零；10/20 mm 起伏面在 roughness 图中颜色不同，但其拟合平面均近水平，因此 slope 接近零。不要将这里的坡度大小当作台阶检测。

- `/terrain_geometry/labels` 是地形名称和指标标题；标签里的角度/毫米数表示数学真值。
- 每条 GridMap 都包含 `elevation`、`slope`、`roughness` 三层。三个话题只是显示位置不同。
- 91×91 地图、0.05 m 分辨率；四个41×41地形块之间留空。只计算完整3×3窗口，边界/缺失格/退化拟合的几何层保持 NaN，不将未知格填成安全平地。
- 当前窗口覆盖0.15×0.15 m格面积，最外侧样本中心间距0.10 m。显示网格使用 column-major 数据，行沿负X、列沿负Y。

消息与指标测试（会编译 C++）：

```bash
source /opt/ros/humble/setup.bash
python3 -m unittest discover -s src/terrain_test/geometry_validation -p test_geometry_demo.py
```

容器或主机均可执行 `check_demo_topics.py`（主机需先复制脚本），环境保持上述 Domain 和 RMW。它真正通过 DDS 订阅三个消息，核对布局、偏移和全部6084个内部格子的高程/坡度/粗糙度；缺失话题20秒超时退出非零。

本次已在主机执行该检查并通过，也实际截图确认 RViz 的三个 GridMap 显示及标签。未测试完整点云融合链路。
