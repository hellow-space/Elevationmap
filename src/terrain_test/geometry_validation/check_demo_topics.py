#!/usr/bin/env python3
"""Verify demo GridMaps received over DDS; can run on the RViz host."""
import math
import time
import rclpy
from grid_map_msgs.msg import GridMap


def main():
    rclpy.init()
    node = rclpy.create_node('check_terrain_geometry_demo')
    received = {}
    subscriptions = []
    for metric in ('elevation', 'slope', 'roughness'):
        subscriptions.append(node.create_subscription(
            GridMap, '/terrain_geometry/'+metric,
            lambda msg, key=metric: received.update({key: msg}), 1))
    deadline = time.monotonic()+20
    try:
        while len(received) < 3 and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.2)
        if len(received) != 3:
            raise RuntimeError(f'Missing topics; received {list(received)}')
        for metric, offset in [('elevation',5.), ('slope',0.), ('roughness',-5.)]:
            msg = received[metric]
            assert msg.header.frame_id == 'map'
            assert msg.layers == ['elevation','slope','roughness']
            assert msg.info.pose.position.y == offset
            assert abs(msg.info.resolution-.05) < 1e-9
            assert abs(msg.info.length_x-4.55) < 1e-9
            assert abs(msg.info.length_y-4.55) < 1e-9
            for data in msg.data:
                assert [d.label for d in data.layout.dim] == ['column_index','row_index']
                assert [d.size for d in data.layout.dim] == [91,91]
                assert len(data.data) == 91*91
            elevation = msg.data[0].data
            slope = msg.data[1].data
            roughness = msg.data[2].data
            for row, col, angle, rms in [(2,2,0.,0.),(2,48,15.,0.),(48,2,0.,.01),(48,48,0.,.02)]:
                for r in range(row+1,row+40):
                    for c in range(col+1,col+40):
                        i=r+91*c
                        expected_height = math.tan(math.radians(angle)) * (20-(r-row)) * .05
                        expected_height += rms / 2 * (1,-2,1)[(r-row)%3] * (1,-2,1)[(c-col)%3]
                        assert abs(elevation[i]-expected_height)<1e-6
                        assert abs(slope[i]-angle)<.001
                        assert abs(roughness[i]-rms)<1e-6
                assert math.isnan(slope[row+91*col])
            print(f'PASS /terrain_geometry/{metric}: received all layers; all 6084 interior cells match truth')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
