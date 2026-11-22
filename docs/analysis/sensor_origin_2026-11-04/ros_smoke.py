"""Domain144 registered-cloud -> real GPU map -> GridMap smoke; no motion commands."""
import os
from pathlib import Path
import time

if os.environ.get('ROS_DOMAIN_ID')!='144' or os.environ.get('ROS_LOCALHOST_ONLY')!='1':
    raise SystemExit('Require isolated ROS_DOMAIN_ID=144 ROS_LOCALHOST_ONLY=1')

import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from geometry_msgs.msg import TransformStamped
from grid_map_msgs.msg import GridMap
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from elevation_mapping_cupy.elevation_mapping_node import ElevationMappingNode

root=Path(__file__).resolve().parents[3]
pkg=root/'src/elevation_mapping_cupy/elevation_mapping_cupy'
args=['--ros-args','--params-file',str(pkg/'config/core/core_param.yaml'),
      '--params-file',str(pkg/'config/setups/raw/elevation.yaml'),
      '-p','map_frame:=review_map','-p','corrected_map_frame:=review_map',
      '-p','base_frame:=review_base','-p','subscribers.depth.topic_name:=/review/cloud',
      '-p','subscribers.depth.sensor_frame:=review_lidar',
      '-p',f'plugin_config_file:={pkg}/config/setups/raw/plugins.yaml']
rclpy.init(args=args)
source=Node('registered_origin_review_source')
mapper=ElevationMappingNode()
executor=SingleThreadedExecutor();executor.add_node(source);executor.add_node(mapper)
pub=source.create_publisher(PointCloud2,'/review/cloud',10)
broadcaster=TransformBroadcaster(source);static=StaticTransformBroadcaster(source)
static_frames=[]
for parent,child,xyz in [('review_map','review_camera',(10.,0.,0.)),
                          ('review_base','review_lidar',(.2,0.,.5))]:
    t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child
    t.transform.translation.x=xyz[0];t.transform.translation.y=xyz[1];t.transform.translation.z=xyz[2]
    t.transform.rotation.w=1.;static_frames.append(t)
static.sendTransform(static_frames)
captured=[];maps=[];state={'base_x':.8}
original=mapper._map.input_pointcloud


def record_input(points,channels,r,origin,*args):
    captured.append((points.copy(),r.copy(),origin.copy()))
    return original(points,channels,r,origin,*args)


mapper._map.input_pointcloud=record_input
sub=source.create_subscription(GridMap,'/elevation_mapping_node/elevation_map',maps.append,10)
x,y=np.meshgrid(np.linspace(.4,1.6,25),np.linspace(-.5,.5,20))
world=np.column_stack([x.ravel(),y.ravel(),np.zeros(x.size)]).astype(np.float32)
cloud_points=world-[10.,0.,0.]


def tick():
    stamp=source.get_clock().now().to_msg()
    t=TransformStamped();t.header.stamp=stamp;t.header.frame_id='review_map';t.child_frame_id='review_base'
    t.transform.translation.x=state['base_x'];t.transform.rotation.w=1.;broadcaster.sendTransform(t)
    m=PointCloud2();m.header.stamp=stamp;m.header.frame_id='review_camera'
    m.fields=[PointField(name=n,offset=i*4,datatype=PointField.FLOAT32,count=1) for i,n in enumerate(['x','y','z'])]
    m.height=1;m.width=len(cloud_points);m.point_step=12;m.row_step=12*m.width
    m.data=cloud_points.astype(np.float32).tobytes();pub.publish(m)


timer=source.create_timer(.05,tick)


def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:executor.spin_once(timeout_sec=.01)


try:
    spin(3.)
    assert len(captured)>=10,(len(captured),len(maps))
    p,r,t=captured[-1]
    np.testing.assert_allclose(t,[1.,0.,.5],atol=1e-5)
    np.testing.assert_allclose(p @ r.T+t,world,atol=2e-6)
    assert maps and maps[-1].header.frame_id=='review_map'
    assert maps[-1].layers==['elevation','variance']
    elev=np.array(maps[-1].data[0].data)
    assert np.isfinite(elev).sum()>=30
    assert np.max(abs(elev[np.isfinite(elev)]))<.01
    print('PASS: registered cloud -> physical origin -> actual GPU fusion -> GridMap',flush=True)
    state['base_x']=1.8;spin(2.)
    p,r,t=captured[-1]
    np.testing.assert_allclose(t,[2.,0.,.5],atol=1e-5)
    np.testing.assert_allclose(p @ r.T+t,world,atol=2e-6)
    print('PASS: sensor origin follows motion while fixed world points stay fixed',flush=True)
    # Stop source timer; no new observation may refresh the map timestamp.
    source.destroy_timer(timer);spin(.2)
    accepted_stamp=mapper._last_t
    m=PointCloud2();m.header.stamp=source.get_clock().now().to_msg();m.header.frame_id='missing_frame'
    m.fields=[PointField(name=n,offset=i*4,datatype=PointField.FLOAT32,count=1) for i,n in enumerate(['x','y','z'])]
    m.height=1;m.width=1;m.point_step=12;m.row_step=12;m.data=np.array([[1.,0.,0.]],dtype=np.float32).tobytes()
    count=len(captured);pub.publish(m);spin(.3)
    assert len(captured)==count and mapper._last_t==accepted_stamp
    print('PASS: rejected TF does not fuse or refresh accepted observation time',flush=True)
finally:
    executor.shutdown();mapper.destroy_node();source.destroy_node();rclpy.shutdown()
