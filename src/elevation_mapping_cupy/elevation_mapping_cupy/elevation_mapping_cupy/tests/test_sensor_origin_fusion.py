"""Real GPU checks for registered-cloud geometry, range noise and height gating."""
import cupy as cp
import numpy as np

from elevation_mapping_cupy import ElevationMap, Parameter
from elevation_mapping_cupy.pointcloud_geometry import sensor_frame_points


def make_map(tmp_path):
    plugins=tmp_path/'no_plugins.yaml';plugins.write_text('{}\n')
    p=Parameter(enable_traversability=False,use_chainer=False,
                plugin_config_file=str(plugins),resolution=.1,map_length=4.,
                enable_visibility_cleanup=False,enable_overlap_clearance=False,
                mahalanobis_thresh=100000.,sensor_noise_factor=.05,max_variance=100.)
    p.update()
    return ElevationMap(p)


def test_registered_fusion_matches_native_sensor_frame_reference(tmp_path):
    x,y=np.meshgrid(np.arange(.45,1.5,.1),np.arange(-.35,.4,.1))
    world=np.column_stack([x.ravel(),y.ravel(),np.full(x.size,-.5)]).astype(np.float32)
    origin=np.array([1.,0.,0.],dtype=np.float32)
    camera=np.array([10.,0.,0.],dtype=np.float32)
    cloud=world-camera
    fixed_points,r,t=sensor_frame_points(cloud,np.eye(3),camera,np.eye(3),origin)
    corrected,reference,legacy=[make_map(tmp_path) for _ in range(3)]
    for _ in range(13):
        corrected.input_pointcloud(fixed_points,['x','y','z'],r,t,0.,0.)
        reference.input_pointcloud(world-origin,['x','y','z'],np.eye(3),origin,0.,0.)
        legacy.input_pointcloud(cloud,['x','y','z'],np.eye(3),camera,0.,0.)
    height=corrected.get_elevation();valid=cp.isfinite(height)
    assert int(valid.sum())>=30
    cp.testing.assert_array_equal(valid,cp.isfinite(reference.get_elevation()))
    cp.testing.assert_allclose(height[valid],reference.get_elevation()[valid],atol=5e-4)
    cp.testing.assert_allclose(corrected.get_variance()[valid],reference.get_variance()[valid],atol=5e-4)
    # The wrong registered-frame origin overestimates range and uncertainty.
    assert float(cp.mean(corrected.get_variance()[valid])) < float(cp.mean(legacy.get_variance()[valid]))


def test_near_sensor_distance_gate_uses_sensor_position(tmp_path):
    corrected,legacy=make_map(tmp_path),make_map(tmp_path)
    cloud=np.array([[-8.95,0.,0.]],dtype=np.float32)  # map x=1.05, physical sensor x=1.
    points,r,t=sensor_frame_points(cloud,np.eye(3),[10.,0.,0.],np.eye(3),[1.,0.,0.])
    for _ in range(13):
        corrected.input_pointcloud(points,['x','y','z'],r,t,0.,0.)
        legacy.input_pointcloud(cloud,['x','y','z'],np.eye(3),np.array([10.,0.,0.]),0.,0.)
    assert int(cp.isfinite(corrected.get_elevation()).sum())==0
    assert int(cp.isfinite(legacy.get_elevation()).sum())>0


def test_ramped_height_gate_is_relative_to_current_sensor(tmp_path):
    corrected,legacy=make_map(tmp_path),make_map(tmp_path)
    cloud=np.array([[-8.5,0.,.8]],dtype=np.float32)  # map point .5m away from current sensor.
    points,r,t=sensor_frame_points(cloud,np.eye(3),[10.,0.,0.],np.eye(3),[1.,0.,0.])
    for _ in range(13):
        corrected.input_pointcloud(points,['x','y','z'],r,t,0.,0.)
        legacy.input_pointcloud(cloud,['x','y','z'],np.eye(3),np.array([10.,0.,0.]),0.,0.)
    assert int(cp.isfinite(corrected.get_elevation()).sum())==0
    assert int(cp.isfinite(legacy.get_elevation()).sum())>0
