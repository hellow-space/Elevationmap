"""Isolated ROS/GPU integration: rolling center vs sub-cell robot movement."""
import math
import os
import signal
import subprocess
import time

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from grid_map_msgs.msg import GridMap
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2, PointField
from tf2_ros import TransformBroadcaster

assert os.environ.get('ROS_DOMAIN_ID') == '197'
rclpy.init()
node = rclpy.create_node('isolated_grid_center_check')
tf = TransformBroadcaster(node)
pub = node.create_publisher(PointCloud2, '/cloud_registered', qos_profile_sensor_data)
received = []
sub = node.create_subscription(GridMap, '/elevation_mapping_node/elevation_map',
                               lambda msg: received.append(msg), qos_profile_sensor_data)
process = None
log = open('/tmp/elevation_grid_center_launch.log', 'w')
try:
    process = subprocess.Popen(
        ['ros2', 'launch', 'elevation_mapping_cupy', 'raw_elevation.launch.py',
         'pointcloud_sensor_frame:=base_link'], stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True)
    # Map-frame points describe a fixed plane, independent of robot translation.
    xs, ys = np.meshgrid(np.linspace(-1.2, 1.2, 40), np.linspace(-1.2, 1.2, 40))
    points = np.column_stack((xs.ravel(), ys.ravel(), np.full(xs.size, -0.5))).astype('<f4')
    base_xy = [0.04, -0.04]
    def send():
        now = node.get_clock().now()
        tr = TransformStamped(); tr.header.frame_id = 'map'; tr.child_frame_id = 'base_link'
        tr.header.stamp = now.to_msg()
        tr.transform.translation.x = base_xy[0]; tr.transform.translation.y = base_xy[1]
        tr.transform.rotation.z = math.sin(0.7 / 2); tr.transform.rotation.w = math.cos(0.7 / 2)
        tf.sendTransform(tr)
        cloud = PointCloud2(); cloud.header.frame_id = 'map'
        cloud.header.stamp = (now - rclpy.duration.Duration(seconds=0.08)).to_msg()
        cloud.height = 1; cloud.width = len(points); cloud.point_step = 12
        cloud.row_step = cloud.width * cloud.point_step
        cloud.fields = [PointField(name=k, offset=i*4, datatype=PointField.FLOAT32, count=1)
                        for i,k in enumerate(('x','y','z'))]
        cloud.data = points.tobytes(); cloud.is_dense = True
        pub.publish(cloud)
    timer = node.create_timer(0.05, send)
    def wait_for_center(want, timeout):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            rclpy.spin_once(node, timeout_sec=0.05)
            for m in received[-10:]:
                if (abs(m.info.pose.position.x-want[0]) < 1e-4 and
                    abs(m.info.pose.position.y-want[1]) < 1e-4 and
                    'elevation' in m.layers and
                    np.isfinite(m.data[m.layers.index('elevation')].data).sum() > 0):
                    assert m.header.frame_id == 'map'
                    assert abs(m.info.length_x - 7.) < 1e-5
                    assert abs(m.info.length_y - 7.) < 1e-5
                    assert m.info.pose.orientation.w == 1.0
                    assert m.info.pose.orientation.x == m.info.pose.orientation.y == m.info.pose.orientation.z == 0.0
                    print('base=',base_xy,'grid=',(m.info.pose.position.x,m.info.pose.position.y),
                          'valid_cells=',np.isfinite(m.data[m.layers.index('elevation')].data).sum(),flush=True)
                    return
            if process.poll() is not None:
                raise RuntimeError('mapping process exited; see /tmp/elevation_grid_center_launch.log')
        raise RuntimeError(f'no fused grid centered at {want}; received {len(received)} maps; see log')
    wait_for_center((0., 0.), 40.)
    received.clear(); base_xy[:] = [0.06, -0.06]
    wait_for_center((0.1, -0.1), 15.)
    print('PASS: real GPU/ROS grid follows position on cell boundaries with map-aligned square',flush=True)
finally:
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.wait()
    log.close(); node.destroy_node(); rclpy.shutdown()
