"""Numerical layers and real ROS message serialization, no mocks."""
import unittest
import numpy as np
from rclpy.serialization import deserialize_message, serialize_message
from grid_map_msgs.msg import GridMap
from validate_geometry import SOURCE, ROOT, build
from geometry_demo import build_demo_layers, make_gridmap, fit_layers


class GeometryDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable = build(SOURCE.read_text(), ROOT / 'build/geometry_validation')
        cls.layers, cls.tiles = build_demo_layers(cls.executable)

    def test_patch_values_and_nan_boundaries(self):
        for tile in self.tiles:
            row, col = tile['origin']
            interior = np.s_[row+1:row+40, col+1:col+40]
            np.testing.assert_allclose(self.layers['slope'][interior], tile['slope_deg'], atol=.001)
            np.testing.assert_allclose(self.layers['roughness'][interior], tile['roughness_m'], atol=1e-6)
            self.assertTrue(np.isnan(self.layers['slope'][row, col:col+41]).all())
        self.assertTrue(np.isnan(self.layers['elevation'][43:48, :]).all())

    def test_gridmap_wire_layout_and_pose(self):
        # Non-square, asymmetric payload catches transpose / row-major mistakes.
        elevation = np.array([[1, 2, 3], [4, 5, np.nan]], dtype=np.float32)
        msg = make_gridmap({'elevation': elevation}, .1, center_y=5.)
        decoded = deserialize_message(serialize_message(msg), GridMap)
        self.assertEqual(decoded.layers, ['elevation'])
        self.assertEqual(decoded.header.frame_id, 'map')
        self.assertEqual(decoded.info.pose.orientation.w, 1.)
        self.assertAlmostEqual(decoded.info.length_x, .2)
        self.assertAlmostEqual(decoded.info.length_y, .3)
        self.assertEqual(decoded.info.pose.position.y, 5.)
        self.assertEqual([d.label for d in decoded.data[0].layout.dim], ['column_index','row_index'])
        self.assertEqual([d.size for d in decoded.data[0].layout.dim], [3, 2])
        self.assertEqual([d.stride for d in decoded.data[0].layout.dim], [6, 2])
        np.testing.assert_allclose(decoded.data[0].data, [1,4,2,5,3,np.nan], equal_nan=True)
        self.assertEqual(decoded.inner_start_index, 0)
        self.assertEqual(decoded.outer_start_index, 0)

    def test_invalid_center_and_degenerate_window_stay_unknown(self):
        heights = np.zeros((5, 5), dtype=np.float32)
        heights[2, 2] = np.nan
        layers = fit_layers(self.executable, heights, .05)
        self.assertTrue(np.isnan(layers['slope'][2,2]))
        degenerate = np.zeros((3, 3), dtype=np.float32)
        layers = fit_layers(self.executable, degenerate, 1e-6)
        self.assertTrue(np.isnan(layers['slope'][1,1]))
        self.assertTrue(np.isnan(layers['roughness'][1,1]))


if __name__ == '__main__':
    unittest.main()
