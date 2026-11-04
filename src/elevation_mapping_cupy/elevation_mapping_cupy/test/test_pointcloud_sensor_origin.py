"""Actual pointcloud callback regressions; no ROS nodes or GPU map needed."""
from types import MethodType, SimpleNamespace

import numpy as np
from geometry_msgs.msg import TransformStamped
from sensor_msgs.msg import PointCloud2, PointField
from tf2_ros import Buffer

from elevation_mapping_cupy.elevation_mapping_node import ElevationMappingNode
from elevation_mapping_cupy import elevation_mapping_node as node_module


def transform(parent, child, xyz, yaw=0., stamp=0):
    t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child
    t.header.stamp.sec=stamp;t.transform.translation.x=float(xyz[0])
    t.transform.translation.y=float(xyz[1]);t.transform.translation.z=float(xyz[2])
    t.transform.rotation.z=float(np.sin(yaw/2));t.transform.rotation.w=float(np.cos(yaw/2))
    return t


def cloud(points, frame='camera_init', stamp=100, extra=False):
    data=np.array(points,dtype=np.float32).reshape(-1,4 if extra else 3)
    m=PointCloud2();m.header.frame_id=frame;m.header.stamp.sec=stamp
    names=['x','y','z','intensity'] if extra else ['x','y','z']
    m.fields=[PointField(name=n,offset=i*4,datatype=PointField.FLOAT32,count=1) for i,n in enumerate(names)]
    m.height=1;m.width=len(data);m.point_step=data.shape[1]*4;m.row_step=m.point_step*m.width
    m.data=data.tobytes();m.is_dense=False
    return m


def harness(sensor_xyz=(1.,0.,0.),sensor_yaw=0.,sensor_stamp=0,with_sensor=True,extra=False,sensor_frame='livox_frame'):
    f=SimpleNamespace(map_frame='map',_last_t=None,_pointcloud_process_counter=0,
        param=SimpleNamespace(subscriber_cfg={'depth':{'sensor_frame':sensor_frame,
            'channels':['intensity'] if extra else []}}),_tf_buffer=Buffer(),calls=[],logs=[])
    f.get_logger=lambda:SimpleNamespace(warning=lambda *a,**k:f.logs.append(a[0]))
    f._map=SimpleNamespace(input_pointcloud=lambda p,ch,r,t,pn,on:f.calls.append((p.copy(),ch,r.copy(),t.copy())))
    for name,method in vars(ElevationMappingNode).items():
        if callable(method) and name!='__init__':setattr(f,name,MethodType(method,f))
    f._tf_buffer.set_transform_static(transform('map','camera_init',(10.,0.,0.)),'test')
    if with_sensor:
        tf=transform('map','livox_frame',sensor_xyz,sensor_yaw,sensor_stamp)
        if sensor_stamp:f._tf_buffer.set_transform(tf,'test')
        else:f._tf_buffer.set_transform_static(tf,'test')
    return f


def test_registered_points_use_current_lidar_origin_not_camera_init_origin():
    f=harness();f.pointcloud_callback(cloud([[-8.,0.,-.2]]),'depth')
    assert len(f.calls)==1
    p,ch,r,t=f.calls[0]
    np.testing.assert_allclose(t,[1.,0.,0.])
    np.testing.assert_allclose(p,[[1.,0.,-.2]])
    np.testing.assert_allclose(p[:,:3] @ r.T+t,[[2.,0.,-.2]])


def test_map_frame_input_still_uses_physical_origin():
    f=harness();f.pointcloud_callback(cloud([[2.,0.,-.2]],frame='map'),'depth')
    p,ch,r,t=f.calls[0]
    np.testing.assert_allclose(t,[1.,0.,0.]);np.testing.assert_allclose(p,[[1.,0.,-.2]])


def test_rotated_sensor_preserves_geometry_and_extra_channels(monkeypatch):
    # Installed ros2_numpy misdecodes FLOAT32 intensity by using field ordinal
    # as byte offset. Isolate that external decoder at the decoded-data boundary;
    # XYZ transport is exercised without this seam in the other callback tests.
    monkeypatch.setattr(node_module.rnp,'numpify',lambda _: {
        'xyz':np.array([[-8.,3.,.5]],dtype=np.float32),
        'intensity':np.array([[42.]],dtype=np.float32)})
    f=harness(sensor_xyz=(1.,2.,0.),sensor_yaw=np.pi/2,extra=True)
    f.pointcloud_callback(cloud([[-8.,3.,.5,42.]],extra=True),'depth')
    p,ch,r,t=f.calls[0]
    np.testing.assert_allclose(p,[[1.,-1.,.5,42.]],atol=1e-6)
    np.testing.assert_allclose(p[:,:3] @ r.T+t,[[2.,3.,.5]],atol=1e-6)
    assert ch==['x','y','z','intensity']


def test_moving_sensor_changes_range_without_moving_world_points():
    outputs=[]
    for x in [1.,5.]:
        f=harness(sensor_xyz=(x,0.,0.));f.pointcloud_callback(cloud([[-8.,0.,-.2]]),'depth')
        outputs.append(f.calls[0])
    np.testing.assert_allclose(outputs[0][0],[[1.,0.,-.2]])
    np.testing.assert_allclose(outputs[1][0],[[-3.,0.,-.2]])
    for p,ch,r,t in outputs:np.testing.assert_allclose(p[:,:3] @ r.T+t,[[2.,0.,-.2]])


def test_native_sensor_input_retains_legacy_geometry():
    f=harness();f.pointcloud_callback(cloud([[1.,0.,-.2]],frame='livox_frame'),'depth')
    p,ch,r,t=f.calls[0];np.testing.assert_allclose(p,[[1.,0.,-.2]])
    np.testing.assert_allclose(t,[1.,0.,0.])


def test_undeclared_sensor_defaults_to_native_message_frame():
    f=harness(sensor_frame='');f.pointcloud_callback(cloud([[1.,0.,-.2]],frame='livox_frame'),'depth')
    p,ch,r,t=f.calls[0];np.testing.assert_allclose(p,[[1.,0.,-.2]])
    np.testing.assert_allclose(t,[1.,0.,0.])


def test_missing_sensor_tf_rejects_without_freshening_observation_time():
    f=harness(with_sensor=False);f.pointcloud_callback(cloud([[-8.,0.,-.2]]),'depth')
    assert not f.calls
    assert f._last_t is None
    assert f._pointcloud_process_counter==0


def test_stale_sensor_tf_is_not_an_unbounded_latest_fallback():
    f=harness(sensor_stamp=99);f.pointcloud_callback(cloud([[-8.,0.,-.2]]),'depth')
    assert not f.calls
    assert f._last_t is None


def test_recent_sensor_tf_fallback_is_allowed_and_uses_actual_origin():
    f=harness(sensor_stamp=100)
    m=cloud([[-8.,0.,-.2]]);m.header.stamp.nanosec=100_000_000
    f.pointcloud_callback(m,'depth')
    assert len(f.calls)==1
    np.testing.assert_allclose(f.calls[0][3],[1.,0.,0.])
    assert any('latest' in line.lower() for line in f.logs)


def test_nonfinite_xyz_does_not_enter_fusion_or_refresh_time():
    f=harness();f.pointcloud_callback(cloud([[float('inf'),0.,0.]]),'depth')
    assert not f.calls
    assert f._last_t is None


def test_zero_stamped_dynamic_tf_does_not_bypass_age_limit():
    f=harness(with_sensor=False)
    f._tf_buffer.set_transform(transform('map','livox_frame',(1.,0.,0.),stamp=0),'test')
    f.pointcloud_callback(cloud([[-8.,0.,-.2]]),'depth')
    assert not f.calls
    assert f._last_t is None
