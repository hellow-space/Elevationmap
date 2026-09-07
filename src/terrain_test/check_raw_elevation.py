#!/usr/bin/env python3
"""Read actual raw GridMap over DDS and check height/variance validity."""
import json
import math
import time
import rclpy
from grid_map_msgs.msg import GridMap


def main():
    rclpy.init()
    node = rclpy.create_node('check_raw_elevation')
    received = []
    sub = node.create_subscription(GridMap, '/elevation_mapping_node/elevation_map', received.append, 1)
    deadline = time.monotonic()+20
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.2)
            if not received:
                continue
            msg = received.pop()
            assert msg.layers == ['elevation', 'variance'], msg.layers
            height, variance = msg.data
            assert len(height.data) == len(variance.data)
            valid = [i for i, value in enumerate(height.data) if math.isfinite(value)]
            if len(valid) < 100:
                continue
            assert all(math.isfinite(variance.data[i]) and variance.data[i] >= 0 for i in valid)
            assert msg.info.resolution > 0
            assert msg.info.pose.orientation.w == 1.
            print(json.dumps(dict(layers=msg.layers, frame=msg.header.frame_id,
                                  resolution_m=msg.info.resolution, valid_cells=len(valid),
                                  height_range_m=[min(height.data[i] for i in valid),max(height.data[i] for i in valid)],
                                  variance_range_m2=[min(variance.data[i] for i in valid),max(variance.data[i] for i in valid)]),indent=2))
            return
        raise RuntimeError('No raw map with at least 100 valid cells received in 20s')
    finally:
        node.destroy_subscription(sub)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
