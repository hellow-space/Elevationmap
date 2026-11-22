"""GridMap metadata must locate the actual rolling grid, not its continuous target."""

from types import SimpleNamespace

import numpy as np
import pytest
from builtin_interfaces.msg import Time
from elevation_mapping_cupy.elevation_mapping_node import ElevationMappingNode
from elevation_mapping_cupy.gridmap_utils import encode_layer_to_multiarray


@pytest.mark.parametrize(
    "grid_center, robot_xy",
    [((0.0, 0.0), (0.04, -0.04)), ((0.1, -0.1), (0.06, -0.06))],
)
def test_publish_uses_grid_center_even_between_cell_shifts(grid_center, robot_xy):
    published = []
    grid = np.arange(4, dtype=np.float32).reshape(2, 2)

    def read_layer(name, buffer):
        assert name == "elevation"
        buffer[:] = grid

    fixture = SimpleNamespace(
        _map_q=SimpleNamespace(x=0., y=0., z=0., w=1.),
        _map_t=SimpleNamespace(x=robot_xy[0], y=robot_xy[1], z=0.),
        _map=SimpleNamespace(resolution=0.1, cell_n=4, get_map_with_name_ref=read_layer),
        _last_t=Time(sec=10),
        _get_map_center=lambda: np.array([*grid_center, 0.], dtype=np.float32),
        map_frame="map",
        _map_data=np.empty((2, 2), dtype=np.float32),
        my_publishers={"elevation_map": {"layers": ["elevation"],
                                         "basic_layers": ["elevation"]}},
        _publishers_dict={"elevation_map": SimpleNamespace(publish=published.append)},
        _numpy_to_multiarray=lambda data, layout: encode_layer_to_multiarray(data, layout=layout),
    )

    ElevationMappingNode.publish_map(fixture, "elevation_map")

    assert len(published) == 1
    msg = published[0]
    assert msg.header.frame_id == "map"
    assert msg.info.pose.position.x == pytest.approx(grid_center[0], abs=1e-7)
    assert msg.info.pose.position.y == pytest.approx(grid_center[1], abs=1e-7)
    assert msg.info.length_x == pytest.approx(0.2)
    assert msg.info.length_y == pytest.approx(0.2)
    assert msg.info.pose.orientation.w == 1.0
    assert list(msg.data[0].data) == [0., 2., 1., 3.]
