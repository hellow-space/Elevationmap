# 四轮足机器人地形评估

更新日期：2026-09-19

## 接手时先看这里

已完成几何函数精度测试和测试地形 RViz 显示。当前新增原始高程模式：真正关闭神经网络权重加载/推理，仅发布融合 elevation/variance，并在主机实际订阅和显示。原始模式仍保留 CuPy 几何融合，尚未把 slope/roughness 接到生产地图。优先使用下方 raw 入口，不把测试夹具结果当作原始建图指标。

阅读顺序：`AGENTS.md`（范围与规则）→ 本文件（进度与下一步）→ `EXPERIENCES.md` 的相关条目（验证过的方法）。只读下一步直接涉及的源码，不要重新扫描大量文件。

## Git 检查点

- 仓库 `/root/elevation_map`，分支 `main`。
- 可运行源码快照：`608adab`，提交说明 `baseline: snapshot working Humble terrain workspace`；“可运行”依据用户确认，本次没有重跑 demo。
- 本交接文档检查点说明：`docs: record workspace handoff and host RViz procedure`。该提交包含根目录 `AGENTS.md`、`EXPERIENCES.md` 和本文件，不修改源码。
- 此检查点的提交号请用下列命令查询，避免在提交内容中硬编码自身提交号。完成提交后预期工作区干净，接手时必须重新查询实际状态，不把本段当作实时状态。

```bash
cd /root/elevation_map
git -c safe.directory=/root/elevation_map branch --show-current
git -c safe.directory=/root/elevation_map log -3 --oneline
git -c safe.directory=/root/elevation_map status --short
```

本环境曾因目录归 UID 1000、执行用户为 root 而触发 Git ownership 检查，以上 `-c` 仅对单次命令信任本工作空间。编译目录 `build/`、`install/`、`log/` 和缓存不入库。没有创建远端或推送；Git 提交只保存在本机。

## 当前基线

- 用户确认：当前工作空间可以成功运行 synthetic demo；本次 Git 建档没有重新验证运行效果。
- 工作空间：`/root/elevation_map`；Git 仓库：`/root/elevation_map`，统一管理 `src/` 下的三个目录。
- ROS 2：Humble。这里发布点云、TF 和高程地图，主环境运行 RViz。
- 按用户要求建立新的工作空间 Git 仓库，分支为 `main`。旧源码仓库元数据已移出工作空间备份；原 HEAD 为 `deb1c86`。
- 当前已有改动包含动态障碍点云、机器人运动 TF、可选静态 map -> odom，以及默认关闭 RViz。
- baseline 保存当前源码原貌；忽略编译产物、Python 缓存等生成文件。
- baseline 包含 `src/elevation_mapping_cupy/`、`src/elevation_nav2_bridge/` 和 `src/terrain_test/`。

## 原始高程模式（当前优先入口）

使用已有点云和 TF：加载 Humble 和 `install/setup.bash` 后执行：

```bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py
```

默认真实点云输入为 `/cloud_registered`，GridMap frame 为 `camera_init`，机器人 frame 为 `base_link`；也可用 launch 参数覆盖。没有真实输入时使用测试入口必须显式将话题覆盖回 `/camera/depth/points`。本次历史测试两端用 Domain43 / CycloneDDS；真实数据源应沿用其 Domain。默认容器不启动 RViz，主机加载 `/tmp/raw_elevation.rviz`。详细命令、接入参数、raw 边界和高程/方差切换见 `src/terrain_test/RAW_ELEVATION.md`。

当前运行中：容器 raw launch 当时 PID1460299（子节点1460357/1460359），主机 RViz 当时 PID3141037。操作前必须核对命令行，勿凭历史 PID 杀进程；旧 geometry_demo 已停止。

## 原有 synthetic demo 运行入口（仍默认启用神经网络）

在数据与建图环境：

```bash
cd /root/elevation_map
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch elevation_mapping_cupy synthetic_depth_demo.launch.py launch_rviz:=false
```

主环境加载 Humble 后执行 `rviz2`，Fixed Frame 使用 `map`。

## 已确认的代码情况

- synthetic demo 发布的 GridMap 层为 `elevation`、`variance`、`traversability`。
- traversability 使用仓库自带卷积权重推理，不是可直接配置最大坡度的几何规则。
- 主建图模块包含相邻格差分法向量计算。
- `plane_segmentation` 包含局部平面拟合、倾角与拟合误差判定；目录有 `COLCON_IGNORE`，不能把源码存在当作已编译可运行。
- 当前 demo 没有直接发布 `slope`、`roughness` 层。

## 目标与待办

- [x] 将 raw 高程 GridMap 的默认 frame 从 `map` 改为 `camera_init`，保留 `base_link` 作为机器人 frame 和 launch 覆盖能力。提交说明：`feat: publish raw elevation in camera_init frame`。

- [x] 将 raw 高程模式的默认真实点云输入改为 `/cloud_registered`，保留 `elevation` 和 `variance` 输出及 launch 参数覆盖能力。提交说明：`feat: use registered cloud for raw elevation input`。

- [x] 核实 `elevation_mapping_cupy` 的官方来源、原始克隆分支与当前核心差异。原始来源为 `leggedrobotics/elevation_mapping_cupy` 的 `ros2` 分支，浅克隆 HEAD 为 `deb1c86789a6873d48c28938d179b980858fd1bb`；差异边界见阶段记录。提交说明：`docs: record elevation mapping upstream provenance`。

- [x] 提供无神经网络的原始融合高程/方差模式，并完成真实 GPU、ROS 话题与主机 RViz 验证。提交说明：`feat: add raw elevation mode without neural traversability`。

- [x] 确认用户现有系统已能运行，记录 Humble 与外部 RViz 使用方式。证据与使用方法已保存于 `3d5e115`（`docs: record workspace handoff and host RViz procedure`）。
- [x] 设计最小几何测试：人工生成已知角度平面，不依赖 Gazebo。
- [x] 确认如何独立调用现有局部平面拟合实现及必要依赖。
- [x] 检验水平面、X/Y 方向斜坡、负向斜坡的法向量、坡度与拟合误差。
- [x] 记录真值、误差、有效格子数、窗口大小和地图分辨率；容差在执行前明确。
- [x] 用解析真值验证 10 mm、20 mm 非零 roughness，并检查带起伏斜坡的拟合角度。以上数值验证统一保存于 `test: validate original plane slope and roughness accuracy`。
- [x] 为已验证的测试地形增加 slope（度）和 roughness（平面距离 RMS，米）的 GridMap 输出并在主环境 RViz 查看。提交说明：`feat: visualize validated terrain geometry in host RViz`。
- [ ] 将相同几何指标接入生产高程地图；当前三个显示话题仅是数学测试地形，不代表原建图输出。
- [ ] 使用同样斜坡的假点云测试完整建图流程，区分几何计算与融合/滤波误差。
- [ ] 后续按四轮足机器人的轮式/迈步模式讨论通过条件，暂不把现有卷积分数视为已适配的通行判据。

## 最小相关源码入口

以下路径均相对于工作空间根目录；先按目标选读，不必全部打开。

| 目标 | 文件 / 入口 |
|---|---|
| Demo 节点与 TF 组合 | `src/elevation_mapping_cupy/elevation_mapping_cupy/launch/synthetic_depth_demo.launch.py` |
| 当前地图输出层 | `src/elevation_mapping_cupy/elevation_mapping_cupy/config/setups/synthetic/synthetic_depth.yaml` |
| 假点云生成 | `src/elevation_mapping_cupy/elevation_mapping_cupy/scripts/synthetic_pointcloud_tf_publisher.py` |
| 局部平面拟合 | `src/elevation_mapping_cupy/plane_segmentation/convex_plane_decomposition/src/sliding_window_plane_extraction/SlidingWindowPlaneExtractor.cpp`：`normalAndErrorFromCovariance`、`computeNormalAndErrorForWindow` |
| 拟合接口与访问范围 | `src/elevation_mapping_cupy/plane_segmentation/convex_plane_decomposition/include/convex_plane_decomposition/sliding_window_plane_extraction/SlidingWindowPlaneExtractor.h` |
| 窗口和倾角/误差阈值 | 同一 include 目录中的 `SlidingWindowPlaneExtractorParameters.h` |
| 平面模块构建依赖 | `src/elevation_mapping_cupy/plane_segmentation/convex_plane_decomposition/CMakeLists.txt`、`package.xml`；先确认依赖，不直接删除父目录 `COLCON_IGNORE` |
| 另一套差分法向量（不要混为拟合算法） | `src/elevation_mapping_cupy/elevation_mapping_cupy/elevation_mapping_cupy/kernels/custom_kernels.py`：`normal_filter_kernel` |

## 已完成的最小验证与下一步

复现命令（自动用 g++ 编译 Eigen 测试适配器并运行）：

```bash
python3 src/terrain_test/geometry_validation/validate_geometry.py --mutation-check
```

- 说明与真值推导：`src/terrain_test/geometry_validation/README.md`。
- 实测快照：`src/terrain_test/geometry_validation/results_2026-09-06.json`，含被测源码 SHA-256、平台和编译器信息。默认复跑结果写入被忽略的 `build/geometry_validation/results.json`。
- 测试在构建时提取仓库原有两个函数，保留函数体，用最小类状态提供窗口大小和分辨率；未验证完整类初始化、GridMap 遍历或分割模块构建。没有删除 `COLCON_IGNORE`。
- 41×41 数学矩阵、3×3 窗口（1521 个/场景），覆盖平地、X/Y ±15°、对角 15°、高度平移、分辨率变化；5×5 窗口场景 1369 个。
- 验收：角度误差 <0.1°、roughness 误差 <0.0001 m、法向量最大分量误差 <1e-5；另检验缺失和共线数据的无效哨兵。17 组通过，3 种临时故障均被检出。
- 普通 15° 平面最大误差约 0.00000531°；10 m 高度平移场景最大误差约 0.000260°，仍通过。10/20 mm roughness 真值误差小于 1e-9 m。
- 15° 斜坡叠加竖直起伏后的正交拟合角为约 15.84248°、RMS 约 9.64021 mm，与解析真值一致；基础坡角与最佳拟合坡角不同，不能混用。

下一步：

1. 先确认要接入的几何层接口，保持同一误差定义；设计无效格掩码，不能将原函数 `1e30` 哨兵对应的向上法向量当作平地。
2. 检查地图格索引与世界坐标映射，确保接入时仍保持法向量方向正确；局部窗口尺寸应明确以米和格数共同记录。
3. 测试地形的 slope/roughness 发布与 RViz 已完成，见下方运行入口；生产地图接入仍待实现。
4. 用已知地形点云验证融合、滤波后的整条链路误差。数学夹具不代表实际传感器或机器人能力；不训练网络、不改 MPPI。

## 环境恢复与验证边界

- 当前已有 Humble 和编译目录；恢复到新环境时，Git 不含编译结果，需要在 Humble 下重新检查依赖并构建。README、docker/src.repos 和 requirements 中存在 Jazzy/CUDA 12 假设，不能直接照搬或更换 ROS 版本。
- 主机：`nvidia@172.26.59.240:22`，桌面 `DISPLAY=:0`。当前容器内未找到 RViz2；通过 SSH 在主机运行，命令与公钥授权步骤见 `EXPERIENCES.md`。
- 专用私钥 `/root/.ssh/elevation_host_rviz` 不在 Git 内。容器删除后不保证保留，恢复时需安全恢复或重新生成密钥并授权公钥；不要提交私钥或密码。
- 主机指纹记录 `/tmp/elevation-map-host-known-hosts` 是临时文件，丢失后重新核实主机指纹并登记。
- 原嵌套 Git 备份 `/tmp/elevation-map-git-backup.MmJenz/original.git` 也是临时备份，不能当作长期备份；新仓库 baseline 已包含当前源码。
- 已验证：SSH 登录主机、主机 RViz2 OpenGL 初始化、受控结束与无残留进程。另已验证：17 组局部拟合数值测试。另已验证：主机订阅测试地形三条 GridMap、逐格核对全部三层，以及 RViz 三图和标签显示。未验证：完整建图链路几何精度、轮足机器人的通过能力。
- 用户要求暂停查看后，已停止本次容器发布程序（PID 358854）并关闭主机 RViz（PID 971428）；操作前核对了各自命令行，未处理其他节点。需要再次查看时按 README 重新启动。

## 阶段记录

### 2026-09-06：主机 RViz2 远程启动验证

- 修改文件：`EXPERIENCES.md`、`PROJECT_STATUS.md`，记录复用方法和验证边界。
- 实际操作：容器通过专用 SSH 密钥登录主机，以 `DISPLAY=:0` 执行 `timeout --signal=INT --kill-after=3s 7s ros2 run rviz2 rviz2`；完整命令见经验记录。
- 实际结果：主机 RViz2 OpenGL 初始化成功；SIGINT 后未及时结束，由 timeout 强制终止（137），随后确认无残留 RViz2。
- 当前问题：尚未验证远程启动后的地图订阅；本次文档更新未重新运行 RViz2、编译或算法测试。
- 下一步：复用已验证的主机执行入口，继续最小几何测试方案；经验记录随文档检查点保存。

### 2026-09-06：文档交接检查点

- 文件：根目录 `AGENTS.md`、`EXPERIENCES.md`、`PROJECT_STATUS.md`。
- 内容：保存用户工作规则、已验证的主机 RViz 方法、源码入口、接手动作、Git 状态查询与恢复条件。
- 验证：检查文档中的本地源码路径、Bash 示例语法、暂存文件范围和提交后工作区状态；结果以提交完成时的终端输出为准。
- 未运行：构建、几何测试和新的 RViz 实验，本次只整理文档。
- 对应提交说明：`docs: record workspace handoff and host RViz procedure`。

## 后续记录规则

### 2026-09-06：完成目标后自动提交

- [x] 在 `AGENTS.md` 明确每完成并验证一个目标就自动本地提交，包含状态和必要经验记录，不再询问是否提交。
- 修改文件：`AGENTS.md`、`PROJECT_STATUS.md`；为已有环境确认目标关联 `3d5e115`，不重复制造 baseline。
- 验证：检查新增规则与用户要求一致，提交前运行 `git diff --check` 并核对暂存范围，提交后核对日志和剩余改动。本次不涉及代码，不运行构建或算法测试。
- 对应提交说明：`docs: require a git checkpoint for each completed goal`。
- 下一步：回到几何算法最小独立验证方案。

每项工作记录：目标、改动、验证命令、实际结果、剩余问题以及对应 Git 提交。
未运行的测试明确标为未运行；不把预计结果记录为实测结果。
按一个明确目标组织一次提交。当前只建立本地版本管理，未创建远端或推送。

### 2026-09-06：局部平面数值精度验证

- 完成目标：验证现有几何函数的坡度、法向量和零/非零 roughness 精度，新增测试而不修改生产算法。
- 文件：`src/terrain_test/geometry_validation/` 的 Python 构建/验证脚本、C++ 输入输出适配器、README、实测 JSON，以及状态和经验记录。
- 实际命令：`python3 src/terrain_test/geometry_validation/validate_geometry.py --mutation-check --output src/terrain_test/geometry_validation/results_2026-09-06.json`。
- 结果：17 组通过，3 种故障注入全部检出；使用真实 Eigen C++ 求解器，独立审阅确认解析真值和适配方法未发现具体问题。
- 首轮构建有 Eigen ARM NEON 头文件警告；正式复跑将第三方 Eigen 目录标为系统头文件，保留本地代码 `-Wall -Wextra` 检查。没有修改 Eigen 或生产算法。
- 边界：未运行 colcon 全包构建、ROS 话题或新的 RViz 实验；本阶段构建的是独立数值验证程序。
- 对应提交说明：`test: validate original plane slope and roughness accuracy`。

### 2026-09-06：测试地形 GridMap 与主机 RViz 可视化

- 完成目标：让用户直接查看已验证几何指标。原生产地图与算法保持不变，当前只是数学测试夹具的 ROS 显示。
- 文件：`src/terrain_test/geometry_validation/geometry_demo.py`、`geometry_demo.rviz`、`test_geometry_demo.py`、`check_demo_topics.py`、同目录 README，以及状态/经验记录。
- 构建和测试：加载 Humble 后运行 `python3 -m unittest discover -s src/terrain_test/geometry_validation -p test_geometry_demo.py`，真实编译 Eigen 适配器，3 项通过（指标/边界、非方阵消息序列化、无效拟合）。新增模块前测试因模块不存在失败，实现后通过。
- 运行：Domain 42、`rmw_cyclonedds_cpp`；容器执行 `python3 src/terrain_test/geometry_validation/geometry_demo.py`，以2 Hz发布；主机执行 `rviz2 -d /tmp/geometry_demo.rviz`。完整重现步骤见同目录 README。
- 实际 DDS 验证：通过 SSH 在主机执行 `/tmp/check_demo_topics.py`，三个话题分别收到3层，每图6084个内部格子的高程、坡度和粗糙度均符合数学真值。
- 实际显示：主机 RViz 日志 OpenGL 4.6 初始化成功；截图核对 Global Status OK、3幅彩色图和地形标签。默认从屏幕左至右为 roughness、slope、height。蓝低红高。
- 截图：`build/geometry_validation/rviz_demo.png`（编译目录被忽略，不在 Git 中；需要时重新截图）。窗口与发布程序已保留供用户查看。
- 独立审阅：没有阻塞性问题；按建议补充了 DDS 高程数值核验，并在主机执行通过。
- 对应提交说明：`feat: visualize validated terrain geometry in host RViz`。
- 下一步：接入实际 elevation map 后验证融合/滤波误差，不将测试地图显示成功当作完整系统通过。

### 2026-09-06：停止可视化演示

- 按用户要求，核对命令行后停止本次测试发布程序并关闭主机 RViz；未修改代码或其他节点。
- 对应提交说明：`docs: record geometry demo shutdown`。

### 2026-09-07：无神经网络的 raw 高程与不确定度

- 新增 `enable_traversability`（默认true保持旧行为）；false时跳过权重/后端/推理、禁用依赖该分数的漂移补偿，可通行性输出未知、多边形查询报禁用。
- 新 raw launch 默认仅建图，支持点云/frames参数，可选择测试输入；空插件配置、关闭启动人工初始化，只发布 elevation/variance。RViz 高度取 elevation，颜色可切换 variance。
- 修改核心参数、初始化与推理条件、ROS参数读取和 CMake 测试注册；新增 raw launch/config/RViz、GPU回归、主机订阅核验脚本及使用文档。
- 构建：`colcon build --packages-select elevation_mapping_cupy --symlink-install` 成功。
- 测试：raw/parameter/gridmap_layout 共6项通过；补强漂移测试后 `colcon test --packages-select elevation_mapping_cupy --ctest-args -R '^test_raw_elevation$' --event-handlers console_direct+` 2项通过；内存故障注入移除漂移guard时如期失败。
- 实测：Domain43 运行 raw launch 测试输入，主机核验收到且仅收到 elevation/variance；单次5723有效格，高度0–0.397068m、方差0.000230091–0.019184548m²。`ros2 param get` 确认开关false。
- 实际主机 RViz 初始化成功并截图核对 Global Status OK 和高程地形；截图在被忽略的 `build/raw-elevation-rviz.png`。窗口和发布节点保留供用户查看。
- 失败教训：3帧融合尚有约1.5mm先验残差；检查融合公式后增加重复观测并验证收敛、方差下降，保留1mm精度门槛。并非原平面拟合测试失败。
- 原始模式不是裸点云，不等于所有过滤均关闭；variance不是roughness。当前仍未在生产地图发布slope/roughness。
- 提交说明：`feat: add raw elevation mode without neural traversability`。

### 2026-09-07：官方分支与本地核心差异核实

- 完成目标：确认 `src/elevation_mapping_cupy` 的上游来源、原克隆分支和当前源码相对官方克隆点的实质差异。
- 来源证据：Shell 历史保留命令 `git clone -b ros2 --depth 1 https://github.com/leggedrobotics/elevation_mapping_cupy.git`；旧嵌套仓库移除前记录的 HEAD 为 `deb1c86`。从官方仓库重新获取后确认完整提交为 `deb1c86789a6873d48c28938d179b980858fd1bb`（`Trim torch CUDA cache in elevation mapping`），由官方 `ros2` 分支包含；该提交自己的 README 也将当前分支标为 `ros2`。
- 比较方法：从官方提交导出干净源码，并分别与统一仓库基线 `608adab`、当前 HEAD 比较。由于本地广泛存在 CRLF、官方快照使用 LF，比较使用 `git diff --ignore-space-at-eol --no-index` 排除换行符假差异，同时排除 `.pytest_cache` 和 `__pycache__` 生成物。
- 基线结果：`608adab` 相对官方 `deb1c86` 只有 `synthetic_depth_demo.launch.py` 和 `synthetic_pointcloud_tf_publisher.py` 两个实质差异，用于默认关闭容器 RViz、增加 map→odom 选项、机器人运动和动态障碍测试点云；生产高程融合、CUDA kernels、traversability filter、plugins 和 plane segmentation 算法一致。
- 当前结果：相对官方克隆点共有 12 个非缓存文件存在实质差异，其中 7 个已修改、5 个新增。除上述两个 synthetic demo 文件外，提交 `fc91357` 为 raw 模式修改 `CMakeLists.txt`、`core_param.yaml`、`elevation_mapping.py`、`elevation_mapping_node.py`、`parameter.py`，并新增两份 raw 配置、raw 测试、launch 和 RViz 配置。
- 核心边界：`elevation_mapping.py` 的权重加载、推理、漂移补偿和查询路径已做小范围条件化，节点与参数类增加开关；点云融合公式、CuPy/CUDA kernel、法向量 kernel、原 traversability 网络计算和局部平面拟合实现未改。
- 当前仓库状态：工作区根目录的新统一 Git 仓库分支为 `main` 且没有 remote；这是后续版本管理结构，不代表原 package 是从官方 `main` 克隆。原临时嵌套 Git 备份现已不存在，因此以已记录 HEAD、Shell 克隆命令和官方仓库提交三方交叉核验。
- 验证：实际执行官方仓库克隆、`git branch -r --contains deb1c86`、提交元数据查询、忽略行尾差异的目录比较，以及 `608adab..HEAD` 提交差异检查。未运行 build、ROS 节点或算法测试；本阶段只调查版本来源和静态源码差异。
- 对应提交说明：`docs: record elevation mapping upstream provenance`。

### 2026-09-19：raw 高程默认接入真实注册点云

- 完成目标：raw 模式默认订阅从 `/camera/depth/points` 改为 `/cloud_registered`；输出仍为 `/elevation_mapping_node/elevation_map`，类型 `grid_map_msgs/msg/GridMap`，包含 `elevation`（m）和 `variance`（m²）。神经网络保持关闭，未修改 MPPI 或几何指标。
- 修改文件：raw YAML、raw launch、launch/config 回归测试、`src/terrain_test/RAW_ELEVATION.md`、状态与必要经验记录。YAML 可修改默认输入，launch 的 `pointcloud_topic` 参数仍可覆盖。
- TDD：新增测试首先因 YAML 返回旧话题 `/camera/depth/points` 而失败；修改后通过。测试同时解析真实 YAML 和 ROS launch 默认 substitution，并锁定 elevation/variance 两层。
- 构建：`colcon build --packages-select elevation_mapping_cupy --symlink-install --event-handlers console_direct+` 成功，1 package finished。
- 完整测试：`colcon test --packages-select elevation_mapping_cupy --event-handlers console_direct+` 共 12 个 CTest 目标，11 个通过；`test_test_map_save_load_services.py` 因当前环境缺少配置要求的 `rosbag2_storage_mcap` 失败。失败发生在 rosbag writer open，与实时高程话题改动无关，不能记为全套测试通过。
- 实际 ROS 接口：在 Domain77 / CycloneDDS、`publish_test_cloud:=false` 启动 raw launch，日志确认神经权重/推理关闭；`ros2 node info` 确认订阅 `/cloud_registered`（PointCloud2），发布 `/elevation_mapping_node/elevation_map`（GridMap）。当前 `/cloud_registered` publisher count 为 0，因此没有首帧和 TF，8 秒内未收到 GridMap 消息；没有把空接口或假数据描述成真实高程结果。
- 当前问题：需要用户的真实点云进程与 TF 同时在线，才能验证实际 elevation/variance 数值及 RViz。地图保存测试另缺 MCAP storage plugin，见 `EXPERIENCES.md`。
- 对应提交说明：`feat: use registered cloud for raw elevation input`。

### 2026-09-20：raw 高程默认 frame 改为 camera_init

- 完成目标：raw YAML 的 `map_frame`、`corrected_map_frame` 以及 raw launch 的默认 `map_frame` 从 `map` 改为 `camera_init`；`base_frame=base_link`、输入 `/cloud_registered`、输出 topic 和 elevation/variance 两层保持不变。
- TDD：新增 frame 回归测试后首先因 YAML 返回 `map` 而失败；最小配置修改后，launch/config 测试3项通过。
- 构建：`colcon build --packages-select elevation_mapping_cupy --symlink-install --event-handlers console_direct+` 成功，1 package finished。
- 完整测试：`colcon test --packages-select elevation_mapping_cupy --event-handlers console_direct+` 共12个 CTest 目标，11个通过；地图保存测试仍因环境缺少 `rosbag2_storage_mcap` 失败。synthetic demo 主体通过后在一次 SIGINT 关闭阶段出现消息转换异常，单独复跑该目标完整通过且节点干净退出；未修改该无关路径。
- 实际 ROS 参数：在 Domain78 / CycloneDDS、无测试点云启动 raw launch，`ros2 param get` 实收 `map_frame=camera_init`、`corrected_map_frame=camera_init`、`base_frame=base_link`、输入 `/cloud_registered`；ROS 图确认发布 `/elevation_mapping_node/elevation_map`。当前 `/cloud_registered` publisher count 为0，因此未声称实际 GridMap header或高度数据已验证。
- 后续真实链路复查：在实际系统 Domain42 / CycloneDDS 中，`/cloud_registered` 有1个 `laserMapping` 发布器且消息 `frame_id=camera_init`，建图节点订阅匹配；`tf2_echo camera_init base_link` 连续收到变换。`check_raw_elevation.py` 实收 GridMap 的 `frame=camera_init`、layers=`elevation,variance`、分辨率0.1m、1027个有效高程格；当帧高度范围约-0.617305～1.587893m，方差范围约0.001338～4.030836m²。由此确认当前真实点云、TF和raw高程发布链路已运行。该数值只是当帧观测，不代表长期范围或精度保证。
- Nav2 边界：静态源码检查确认当前 `elevation_nav2_bridge` 直接把 GridMap 世界坐标用于 master costmap，不执行 TF frame 转换；接入时 local costmap `global_frame` 必须与 GridMap 的 `camera_init` 一致，`robot_base_frame` 使用 `base_link`。本阶段未运行 Nav2/MPPI。
- 对应提交说明：`feat: publish raw elevation in camera_init frame`。
