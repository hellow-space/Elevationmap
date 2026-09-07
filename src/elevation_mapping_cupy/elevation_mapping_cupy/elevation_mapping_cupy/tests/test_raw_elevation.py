"""Raw mode must fuse real GPU data without loading neural weights/backends."""
import sys
import numpy as np
import cupy as cp
import pytest
from elevation_mapping_cupy import ElevationMap, Parameter


def test_raw_fusion_without_weights_or_neural_backend(tmp_path):
    plugins = tmp_path / 'empty.yaml'
    plugins.write_text('{}\n')
    neural_modules_before = {m for m in sys.modules if m.split('.')[0] in ('torch','chainer')}
    p = Parameter(enable_traversability=False, use_chainer=False,
                  weight_file=str(tmp_path / 'does-not-exist.dat'),
                  plugin_config_file=str(plugins), resolution=.1, map_length=4.,
                  enable_visibility_cleanup=False, enable_overlap_clearance=False,
                  min_height_drift_cnt=1)
    p.update()
    mapping = ElevationMap(p)
    assert mapping.traversability_filter is None
    x, y = np.meshgrid(np.linspace(.4, 1.2, 30), np.linspace(-.4, .4, 30))
    points = np.column_stack((x.ravel(), y.ravel(), np.full(x.size, -.5))).astype(np.float32)
    for _ in range(3):
        mapping.input_pointcloud(points, ['x','y','z'], np.eye(3), np.zeros(3), 0., 0.)
    early_height = mapping.get_elevation()
    early_valid = cp.isfinite(early_height)
    early_error = float(cp.max(cp.abs(early_height[early_valid] + .5)))
    early_variance = mapping.get_variance().copy()
    # Fusion has a finite zero-height prior; repeated measurements must converge.
    for _ in range(10):
        mapping.input_pointcloud(points, ['x','y','z'], np.eye(3), np.zeros(3), 0., 0.)
    height = mapping.get_elevation()
    variance = mapping.get_variance()
    valid = cp.isfinite(height)
    assert int(valid.sum()) >= 20
    assert float(cp.max(cp.abs(height[valid] + .5))) < early_error
    assert bool((variance[early_valid] < early_variance[early_valid]).all())
    cp.testing.assert_allclose(height[valid], -.5, atol=.001)
    assert bool(cp.isfinite(variance[valid]).all())
    assert bool((variance[valid] > 0).all())
    assert bool(cp.isnan(mapping.get_traversability()).all())
    assert neural_modules_before == {m for m in sys.modules if m.split('.')[0] in ('torch','chainer')}
    with pytest.raises(RuntimeError, match='disabled'):
        mapping.get_polygon_traversability(np.zeros((3, 2)), np.zeros(3))
    # A changed surface and high pose noise would otherwise activate drift correction.
    shifted = points.copy()
    shifted[:, 2] += .001
    mapping.input_pointcloud(shifted, ['x','y','z'], np.eye(3), np.zeros(3), 1., 1.)
    assert float(mapping.additive_mean_error) == 0.
    mapping.clear()
    assert bool(cp.isnan(mapping.get_traversability()).all())


def test_default_mode_still_requires_weights(tmp_path):
    plugins = tmp_path / 'empty.yaml'
    plugins.write_text('{}\n')
    p = Parameter(weight_file=str(tmp_path/'missing.dat'), plugin_config_file=str(plugins), map_length=2.)
    p.update()
    with pytest.raises(FileNotFoundError):
        ElevationMap(p)
