# Registered point clouds and the physical sensor origin

The fusion kernels expect XYZ in the physical sensor frame. They use those XYZ
for range-dependent measurement noise, and use the same R,t for map placement,
distance/height gates and visibility-ray origin. A registered cloud in a fixed
world frame cannot pass its frame origin as the current sensor position.

The ROS point-cloud adapter now distinguishes cloud coordinates and sensor
origin. For a cloud `C`, physical sensor `S` and map `M`:

```text
p_S = R_MS.T @ (R_MC @ p_C + t_MC - t_MS)
p_M = R_MS @ p_S + t_MS
```

Map geometry remains unchanged. The existing GPU API and CUDA kernels are
unchanged, while measurement noise and ray origin now use sensor-relative data.
The CPU adapter preserves decoded extra columns and removes nonfinite XYZ.

## Configuration

Each point-cloud subscriber can specify:

```yaml
subscribers:
  depth:
    topic_name: /cloud_registered
    data_type: pointcloud
    sensor_frame: livox_frame
    max_tf_age: 0.2
```

`sensor_frame` is the physical optical/range origin, not automatically the cloud
message frame or base_link. With no configured sensor frame, native sensor-frame
input remains compatible by using its own message frame.

The raw real-data launch defaults to `livox_frame`. Other hardware can override:

```bash
ros2 launch elevation_mapping_cupy raw_elevation.launch.py \
  pointcloud_sensor_frame:=my_lidar
```

For the optional `publish_test_cloud:=true` generator, the origin automatically
uses `base_frame`, matching that generator's points. GridMap frame and robot
tracking frame are separate from the physical sensor frame.

Exact observation-time TF is attempted without blocking. If extrapolation
requires a latest-transform fallback, its timestamp must be no later than the
cloud and at most `max_tf_age` old. Accepted fallback produces a throttled
warning. Static TF is accepted through successful exact-time lookup; a dynamic
zero-stamped latest transform cannot bypass the age limit. Missing/stale TF
discards the frame without advancing the last accepted observation timestamp.

## Validation performed, 2026-11-04

- Package build succeeded in the existing Humble/CUDA container.
- 18 focused tests passed: actual callback, launch substitutions, decoded extra
  channel preservation, and real GPU reference fusion/distance/height gates.
- Independent review re-ran callback tests and checked 100 random full 3D
  transforms. Additional attributes stayed unchanged; float32 world-point error
  was at most 0.046 mm with translations up to 100 m.
- Isolated ROS domain144 exercised actual PointCloud2 and TF subscriptions,
  physical-origin GPU fusion and GridMap output. Moving the sensor changed the
  origin while fixed world points stayed fixed. Rejected frames did not refresh
  accepted observation time. No velocity publishers were created.
- CPU-only synthetic timing for 18000 points: P50 1.336 ms, P95 1.373 ms, max
  1.432 ms (200 measurements after 30 warmups). This excludes TF, DDS, parsing,
  GPU fusion and robot motion; it is not end-to-end performance evidence.
- Full colcon run: 15 CTest groups, 6 failed. The failures originate in default
  neural-mode tests requiring PyTorch, whose import fails because
  `libcudss.so.0` is absent. The three launch-test groups consequently could not
  get a running mapper/map/service. Total reported 64 test cases:10 errors,
  10 failures,0 skipped. These are recorded, not described as passing. Raw-mode
  fusion and the new domain144 transport test do not load that neural backend.

Tests failing due to the existing neural dependency:
`test_map_shifting`, `test_map_services`, `test_kernel_compile_smoke`,
`test_test_tf_gridmap_integration.py`, `test_test_map_save_load_services.py`,
`test_test_synthetic_demo_launch.py`. MCAP storage is also unavailable in this
container; map-save behavior was not reached because the neural mapper failed
to start. No unrelated dependency stack was installed or changed.

## Limits

- This change does not change LiDAR point rate, installation field of view,
  FAST-LIVO timestamps, motion control, or add new ROI/body/height filtering.
- Correct physical-origin TF still depends on calibrated extrinsics. The known
  IMU/LiDAR origin discrepancy of about 5.5 cm in the external LIVO setup was
  not changed here. This fix removes the fixed-world-origin error, not all
  extrinsic calibration error.
- The installed ros2_numpy extra-attribute decoder has a pre-existing intensity
  offset/datatype defect. The default raw XYZ path avoids it. A callback test
  isolates this dependency at its decoded-data boundary; preservation by the
  new affine adapter is independently tested. Full semantic-field decoding is
  not claimed fixed.
- TF header freshness cannot reveal old measurements republished with a current
  timestamp. Upstream acquisition/processing-time diagnostics remain necessary.
- Existing user changes to map-frame defaults and other configuration/documents
  were preserved separately; this commit stages only the origin fix increments.
- Field elevation quality, navigation stability and end-to-end timing still
  require a new recording. The old navigation bag lacks raw IMU/LiDAR inputs.

Evidence and reproduction scripts are in `docs/analysis/sensor_origin_2026-11-04`.
