#!/usr/bin/env python3

import math
import struct
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class FakeTerrainCloud(Node):
    def __init__(self):
        super().__init__('fake_terrain_cloud')

        self.pub = self.create_publisher(PointCloud2, '/camera/depth/points', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.timer = self.create_timer(0.1, self.timer_callback)

        self.get_logger().info('Fake terrain cloud started')

    def publish_tf(self):
        now = self.get_clock().now().to_msg()

        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = 'map'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = 0.0
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(t)

    def height(self, x, y):
        # 基础缓坡
        z = 0.12 * x

        # 台阶：x > 1.0 后整体升高
        if x > 1.0:
            z += 0.35

        # 中间土包
        z += 0.45 * math.exp(-((x - 0.0) ** 2 + (y - 0.0) ** 2) / 0.35)

        # 左侧坑
        if (x + 1.0) ** 2 + (y - 0.5) ** 2 < 0.35 ** 2:
            z -= 0.35

        return z

    def timer_callback(self):
        self.publish_tf()

        points = []
        resolution = 0.05

        x_min, x_max = -2.5, 2.5
        y_min, y_max = -2.5, 2.5

        x = x_min
        while x <= x_max:
            y = y_min
            while y <= y_max:
                z = self.height(x, y)
                points.append((x, y, z))
                y += resolution
            x += resolution

        msg = PointCloud2()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'

        msg.height = 1
        msg.width = len(points)
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        msg.is_bigendian = False
        msg.point_step = 12
        msg.row_step = msg.point_step * len(points)
        msg.is_dense = True
        msg.data = b''.join([struct.pack('fff', *p) for p in points])

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FakeTerrainCloud()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
