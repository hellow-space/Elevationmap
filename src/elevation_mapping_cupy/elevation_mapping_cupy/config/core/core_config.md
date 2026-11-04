/elevation_mapping_node:
  ros__parameters:

    #### 基础参数 ########

    drift_compensation_variance_inlier: 0.1
    # 漂移补偿时用于判断“可信高程单元”的方差阈值。
    # 方差较小、较可信的 cell 才更适合用于估计地图整体高度漂移。

    checker_layer: 'elevation'
    # 判断 GridMap 某个 cell 是否有效时使用的参考 layer。
    # 这里直接使用 elevation 层。

    initialized_variance: 10.0
    # 地图初始化器生成初始高程区域时使用的方差。
    # 注意：它和下面的 initial_variance 不是一回事。
    # initialized_variance：初始化器主动填出来的 cell 的不确定度。
    # initial_variance：普通“未知 cell”最开始的默认方差。

    resolution: 0.1
    # GridMap 分辨率，单位 m/cell。
    # 0.1 = 每个格子 10 cm × 10 cm。

    map_length: 7.0
    # 局部高程图边长，单位 m。
    # 当前配置为 7m × 7m 的局部地图。

    sensor_noise_factor: 0.05
    # 点云高度测量噪声系数。
    # 点离传感器越远，测量方差通常越大。
    # 用于计算每个新点参与高程融合时的 measurement variance。

    mahalanobis_thresh: 2.0
    # 新点与当前 cell 高程差异的离群判断阈值。
    # 新点与已有高程相差太大时，不直接正常融合，
    # 而倾向于按 outlier 处理。
    #
    # 越小：越保守，旧地图越难被新高度改变。
    # 越大：更容易接受与当前高度差异较大的新点。

    outlier_variance: 0.01
    # 当新点被认为是 outlier 时，
    # 给当前 cell 增加多少方差。
    # 意思是：出现冲突观测后，降低对旧高度的信心。

    max_drift: 0.1
    # 允许执行高度漂移补偿的最大漂移量，单位 m。
    # 超过该值认为可能不是普通漂移，为安全起见不进行补偿。

    drift_compensation_alpha: 0.1
    # 漂移补偿的平滑更新系数。
    # 越大修正越快，越小越平滑。

    time_variance: 0.0001
    # 随时间给 cell 增加的不确定度。
    # 地图长期没有被重新观测时，逐渐降低对旧高度的信心。

    max_variance: 100.0
    # 单个 cell 允许的最大方差。
    # 方差过大意味着该 cell 的高程已经非常不可信。

    initial_variance: 1000.0
    # 一个尚未被可靠观测的 cell 的初始方差。
    # 设置很大代表：
    # “我一开始完全不知道这里有多高。”
    #
    # 所以第一批有效点进入时，对 cell 高度影响会非常大。

    traversability_inlier: 0.9
    # 漂移补偿时使用的 traversability 阈值。
    # 只有可通行性较高的 cell 才拿来辅助漂移估计。

    dilation_size: 3
    # traversability 计算前进行膨胀/邻域填充时的窗口大小。
    # 主要服务于后续地形分析，并不是直接控制 elevation 融合。

    wall_num_thresh: 20
    # 一个 cell 中累计点数超过该阈值时，
    # 会认为它可能属于墙、边缘等竖直结构。
    #
    # 此后倾向于保留更高的点，
    # 避免较低点不断把墙的高程“拉下来”，
    # 从而让墙/台阶边缘更加锐利。

    min_height_drift_cnt: 100
    # 至少有这么多个有效 cell，
    # 才允许进行整体高度漂移补偿。
    # 防止有效数据太少时误估漂移。

    position_noise_thresh: 0.01
    # 机器人位置变化超过该阈值时，
    # 才认为发生了值得处理的位置变化。
    # 用于漂移检测相关逻辑。

    orientation_noise_thresh: 0.01
    # 机器人姿态变化超过该阈值时，
    # 才认为发生了值得处理的姿态变化。

    position_lowpass_alpha: 0.2
    # 位置变化检测使用的低通滤波系数。
    # 用来减少位置噪声对运动判断的影响。

    orientation_lowpass_alpha: 0.2
    # 姿态变化检测使用的低通滤波系数。

    min_valid_distance: 0.1
    # 距离传感器小于该值的点直接过滤。
    # 0.1 = 10 cm 内的点不使用。

    max_height_range: 10.5
    # 点相对传感器“向上”的最大允许高度。
    # 超过该高度的点直接过滤。
    # 主要用于去除天花板等高处结构。
    #
    # 你这里 10.5m 很宽，基本不会成为室内高点被过滤的主要原因。

    ramped_height_range_a: 0.3
    # 距离越远时，允许高度上限增加的斜率。
    #
    # 高度门限公式大致为：
    # max(d - b, 0) * a + c

    ramped_height_range_b: 1.0
    # 从距离传感器多少米以后，
    # 高度上限才开始随着距离增加。
    #
    # 这里 = 1m：
    # 1m以内，高度上限基本由 c 决定。

    ramped_height_range_c: 0.2
    # 近距离区域允许的基础高度。
    #
    # 注意：
    # 这不是“地图初始高度 = 0.2m”！
    #
    # 它只是点云过滤阈值。
    #
    # 当前配置：
    # 1m以内，高于传感器约 0.2m 的点可能被过滤。

    update_variance_fps: 5.0
    # 每秒更新地图 cell 方差的频率。
    # 这里 5 Hz。

    update_pose_fps: 10.0
    # 每秒更新机器人位姿、移动局部地图中心的频率。
    # 这里 10 Hz。

    time_interval: 0.1
    # time layer 的时间更新间隔，单位 s。
    # 用于记录某个 cell 多久没有被重新观测。

    map_acquire_fps: 5.0
    # 从 GPU 内存读取当前 raw elevation map 的频率。
    # 这里 5 Hz。
    #
    # 注意：
    # 点云内部融合频率可以高于最终 GridMap 发布/读取频率。

    publish_statistics_fps: 1.0
    # 发布统计信息的频率。

    recordable_fps: 3.0
    # 用于可记录/调试 PointCloud 输出的限制频率。
    # 主要用于减少调试点云的数据量。

    enable_normal_arrow_publishing: false
    # 是否发布地表法向量箭头可视化。
    # false = 不发布。


    #### 地图保存 / 服务参数 ########

    masked_replace_service_mask_layer_name: 'mask'
    # masked replace 服务使用哪个 GridMap layer 作为 mask。

    save_map_default_topic: 'elevation_map'
    # 保存地图时默认保存的 topic / map 名称。

    save_map_storage_id: 'mcap'
    # 保存 rosbag 时使用的存储格式。
    # 这里使用 MCAP。

    service_namespace: '/elevation_mapping_cupy'
    # elevation_mapping_cupy 提供 service 时使用的 namespace。


    #### Visibility Cleanup / Ray Tracing ########

    max_ray_length: 10.0
    # Visibility Cleanup 射线追踪的最大长度，单位 m。
    # 不会沿一条雷达射线无限清理地图。

    cleanup_step: 0.1
    # Visibility Cleanup 判断某个 cell 被射线穿透时，
    # 每次减少该 cell validity 的幅度。
    #
    # 多次被射线证明“这里其实不该有表面”后，
    # cell 会逐渐失效。

    cleanup_cos_thresh: 0.1
    # Visibility Cleanup 中射线方向和表面法向之间的夹角判断阈值。
    # 用来避免把某些接近墙面/竖直面的结构错误清掉。


    #### 可通行性判断相关 ########

    safe_thresh: 0.7
    # traversability 低于该值时，
    # cell 被认为是不够安全的区域。

    safe_min_thresh: 0.4
    # polygon 内只要存在低于该值的 cell，
    # 整个 polygon 就可以被判断为不安全。

    max_unsafe_n: 10
    # polygon 内 traversability < safe_thresh 的 cell
    # 超过这个数量时，polygon 判为 unsafe。


    #### 多楼层 / 重叠地图清理 ########

    overlap_clear_range_xy: 4.0
    # 多楼层/重叠地图清理时考虑的 XY 范围，单位 m。

    overlap_clear_range_z: 2.0
    # 多楼层/重叠地图清理时考虑的 Z 高度范围，单位 m。
    # 超出该高度范围的重叠 cell 可以被清理。


    #### 坐标系 ########

    map_frame: 'odom'
    # Elevation Map 使用的世界/地图坐标系。
    # 地图中的 elevation z 都是在这个 frame 下定义的。
    #
    # 你自己的 launch 里已经覆盖为了：
    # map_frame = map

    base_frame: 'base_link'
    # 机器人本体坐标系。
    # 局部高程图通常以这个 frame 的位置作为地图中心。

    corrected_map_frame: 'odom'
    # 进行 drift compensation 后使用的修正地图坐标系。
    #
    # 你自己的 launch 里同样覆盖为 map。


    #### 功能开关 ########

    enable_edge_sharpen: true
    # 是否开启墙/台阶边缘锐化。
    #
    # 点很多的竖直结构会倾向保留较高点，
    # 避免墙面被平均成一个很低的坡。

    enable_visibility_cleanup: true
    # 是否开启基于传感器射线的 visibility cleanup。
    #
    # 如果一条真实测量射线穿过某个旧的高程 cell，
    # 说明该旧表面可能已经不存在/是伪影，
    # 会逐渐降低该 cell 的有效性。

    enable_drift_compensation: true
    # 是否自动进行地图高度漂移补偿。

    enable_overlap_clearance: true
    # 是否进行多楼层 / 重叠表面的清除。

    enable_pointcloud_publishing: false
    # 是否发布 elevation mapping 内部处理后的点云。
    # 调试时可以开启，但会增加数据量。

    enable_drift_corrected_TF_publishing: false
    # 是否发布经过漂移补偿后的 TF。


    #### Traversability 神经网络 ########

    enable_traversability: true
    # 是否运行 traversability 推理。
    #
    # true：
    # 根据 elevation 等信息计算 traversability。
    #
    # false：
    # 只做高程图，不运行神经网络可通行性。
    #
    # 你目前只需要 elevation + variance 的话，
    # 通常可以关闭。

    use_chainer: false
    # traversability 网络使用哪个 backend。
    #
    # false = PyTorch GPU backend
    # true  = Chainer backend


    #### Upper Bound ########

    use_only_above_for_upper_bound: false
    # upper-bound 相关逻辑是否只考虑位于当前表面上方的数据。
    # 主要服务于遮挡/未知表面的限制与清理。


    #### 地图初始化器 ########

    initialize_method: 'linear'
    # 地图初始化区域的插值方式。
    #
    # 可选：
    # nearest
    # linear
    # cubic

    initialize_frame_id: ['base_link']
    # 启动时使用哪些 TF frame 来初始化地图高度。
    #
    # 这里就是：
    # 使用 base_link 的 Z 高度
    # 在机器人周围初始化一块地图。

    initialize_tf_offset: [0.0]
    # 初始化高度相对 TF frame 的额外 Z 偏移。
    #
    # 当前：
    # elevation_init = base_link.z + 0.0

    dilation_size_initialize: 2
    # 初始化完成后对初始化区域进行膨胀/扩展的大小。

    initialize_tf_grid_size: 1.0
    # 使用一个 TF 初始化地图时，
    # 在该 TF 周围初始化的方形区域大小。
    #
    # 如果 initialize_frame_id 数量 > 3，
    # 该参数不使用。

    use_initializer_at_start: true
    # 节点启动时是否立即运行地图初始化器。
    #
    # 这个参数非常重要。
    #
    # true：
    # 节点一启动，就会在 base_link 周围先填一块“初始高程”。
    #
    # 后面的真实点云是在这个初始地图基础上继续融合。
    #
    # false：
    # 启动时地图保持 unknown，
    # 等真实点云自己建立 elevation。


    #### 插件配置 ########

    # plugin_config_file
    # 插件配置文件路径。
    # 你的 launch 文件里通过：
    #
    # plugin_config_file:
    #   raw/plugins.yaml
    #
    # 传入。