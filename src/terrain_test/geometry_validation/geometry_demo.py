#!/usr/bin/env python3
"""Publish explicitly synthetic test terrain and original C++ fitted geometry."""
import math
import subprocess

import numpy as np
import rclpy
from rclpy.node import Node
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray, MultiArrayDimension
from visualization_msgs.msg import Marker, MarkerArray
from validate_geometry import SOURCE, ROOT, build

RESOLUTION = .05


def fit_layers(executable, heights, resolution):
    """Fit complete 3x3 windows; leave edges, missing data and invalid fits NaN."""
    heights = np.asarray(heights, dtype=np.float32)
    slope = np.full_like(heights, np.nan)
    roughness = np.full_like(heights, np.nan)
    indices, lines = [], []
    for row in range(1, heights.shape[0] - 1):
        for col in range(1, heights.shape[1] - 1):
            patch = heights[row-1:row+2, col-1:col+2]
            if not np.isfinite(patch).all():
                continue
            indices.append((row, col))
            lines.append(f'3 {resolution} ' + ' '.join(map(str, patch.ravel().tolist())))
    if indices:
        result = subprocess.run([str(executable)], input='\n'.join(lines)+'\n',
                                capture_output=True, text=True, check=True)
        rows = result.stdout.splitlines()
        if len(rows) != len(indices):
            raise RuntimeError('C++ fitter returned wrong number of windows')
        for index, values in zip(indices, rows):
            nx, ny, nz, mse = map(float, values.split())
            if not all(math.isfinite(v) for v in (nx, ny, nz, mse)) or mse < 0 or mse >= 1e30:
                continue
            slope[index] = math.degrees(math.atan2(math.hypot(nx, ny), nz))
            roughness[index] = math.sqrt(mse)
    return dict(elevation=heights, slope=slope, roughness=roughness)


def build_demo_layers(executable):
    heights = np.full((91, 91), np.nan, dtype=np.float32)
    tiles = [
        dict(name='FLAT', origin=(2, 2), slope_deg=0., roughness_m=0.),
        dict(name='RAMP 15 deg', origin=(2, 48), slope_deg=15., roughness_m=0.),
        dict(name='ROUGH 10 mm', origin=(48, 2), slope_deg=0., roughness_m=.01),
        dict(name='ROUGH 20 mm', origin=(48, 48), slope_deg=0., roughness_m=.02),
    ]
    for tile in tiles:
        row, col = tile['origin']
        x = (20 - np.arange(41)) * RESOLUTION
        q = np.array([1., -2., 1.])[np.arange(41) % 3]
        patch = math.tan(math.radians(tile['slope_deg'])) * x[:, None] + np.zeros((41,41))
        patch += tile['roughness_m'] / 2 * q[:, None] * q[None, :]
        heights[row:row+41, col:col+41] = patch
    return fit_layers(executable, heights, RESOLUTION), tiles


def make_gridmap(layers, resolution, center_y=0.):
    msg = GridMap()
    msg.header.frame_id = 'map'
    rows, cols = layers['elevation'].shape
    msg.info.resolution = float(resolution)
    msg.info.length_x = rows * resolution
    msg.info.length_y = cols * resolution
    msg.info.pose.position.y = float(center_y)
    msg.info.pose.orientation.w = 1.
    msg.layers = list(layers)
    msg.basic_layers = ['elevation']
    for layer in layers.values():
        array = np.asarray(layer, dtype=np.float32)
        if array.shape != (rows, cols):
            raise ValueError('All map layers must have identical shapes')
        data = Float32MultiArray()
        data.layout.dim = [MultiArrayDimension(label='column_index', size=cols, stride=rows*cols),
                           MultiArrayDimension(label='row_index', size=rows, stride=rows)]
        data.data = array.flatten(order='F').tolist()
        msg.data.append(data)
    return msg


def make_labels(tiles):
    markers = MarkerArray()
    for metric, center_y, title in [('elevation', 5., 'HEIGHT (m)'),
                                    ('slope', 0., 'SLOPE (deg) - 0 to 20'),
                                    ('roughness', -5., 'ROUGHNESS (m) - 0 to 0.02')]:
        entries = [(3., center_y, .7, title)]
        for tile in tiles:
            row, col = tile['origin']
            x = (45 - (row+20)) * RESOLUTION
            y = center_y + (45 - (col+20)) * RESOLUTION
            entries.append((x, y, .65, tile['name']))
        for x, y, z, label in entries:
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.ns = 'geometry_test_labels'
            marker.id = len(markers.markers)
            marker.type = Marker.TEXT_VIEW_FACING
            marker.action = Marker.ADD
            marker.pose.position.x = x
            marker.pose.position.y = y
            marker.pose.position.z = z
            marker.pose.orientation.w = 1.
            marker.scale.z = .19
            marker.color.r = marker.color.g = marker.color.b = marker.color.a = 1.
            marker.text = label
            markers.markers.append(marker)
    return markers


class GeometryDemo(Node):
    def __init__(self, layers, tiles):
        super().__init__('terrain_geometry_demo')
        self.outputs = []
        for metric, offset in [('elevation',5.), ('slope',0.), ('roughness',-5.)]:
            topic = '/terrain_geometry/' + metric
            self.outputs.append((self.create_publisher(GridMap, topic, 1),
                                 make_gridmap(layers, RESOLUTION, offset)))
        self.labels = make_labels(tiles)
        self.label_pub = self.create_publisher(MarkerArray, '/terrain_geometry/labels', 1)
        self.timer = self.create_timer(.5, self.publish)
        for tile in tiles:
            row, col = tile['origin']
            region = np.s_[row+1:row+40, col+1:col+40]
            self.get_logger().info(f"{tile['name']}: slope={np.mean(layers['slope'][region]):.6f} deg, "
                                   f"roughness={np.mean(layers['roughness'][region]):.8f} m")
        self.get_logger().info('Synthetic geometry test only; publishing 3 GridMaps and labels at 2 Hz.')

    def publish(self):
        stamp = self.get_clock().now().to_msg()
        for publisher, msg in self.outputs:
            msg.header.stamp = stamp
            publisher.publish(msg)
        for marker in self.labels.markers:
            marker.header.stamp = stamp
        self.label_pub.publish(self.labels)


def main():
    executable = build(SOURCE.read_text(), ROOT / 'build/geometry_validation')
    layers, tiles = build_demo_layers(executable)
    rclpy.init()
    node = GeometryDemo(layers, tiles)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
