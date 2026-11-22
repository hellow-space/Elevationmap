"""Evaluate actual launch substitutions for real and generated point clouds."""
import importlib.util
from pathlib import Path

import numpy as np
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, SetLaunchConfiguration
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters

from elevation_mapping_cupy.pointcloud_geometry import sensor_frame_points


def test_extra_attributes_survive_reexpression_and_input_is_not_mutated():
    points=np.array([[-8.,3.,.5,42.,7.],[np.nan,0.,0.,99.,8.]],dtype=np.float32)
    original=points.copy()
    r=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    output,rotation,origin=sensor_frame_points(points,np.eye(3),[10.,0.,0.],r,[1.,2.,0.])
    np.testing.assert_allclose(output,[[1.,-1.,.5,42.,7.]],atol=1e-6)
    np.testing.assert_array_equal(points,original)


def load_raw_launch():
    path=Path(__file__).resolve().parents[1]/'launch/raw_elevation.launch.py'
    spec=importlib.util.spec_from_file_location('raw_origin_launch_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.generate_launch_description()


def launch_parameters(overrides):
    context=LaunchContext();context.launch_configurations.update(overrides)
    entities=load_raw_launch().entities
    for action in entities:
        if isinstance(action,(DeclareLaunchArgument,SetLaunchConfiguration)):action.visit(context)
    node=next(n for n in entities if isinstance(n,Node) and perform_substitutions(
        context,normalize_to_list_of_substitutions(n.node_executable))=='elevation_mapping_node.py')
    evaluated=evaluate_parameters(context,node._Node__parameters)
    merged={}
    for item in evaluated:
        if isinstance(item,dict):merged.update(item)
    return merged


def test_real_raw_default_uses_livox_origin():
    params=launch_parameters({})
    assert params['subscribers.depth.sensor_frame']=='livox_frame'


def test_real_raw_origin_can_be_overridden():
    params=launch_parameters({'pointcloud_sensor_frame':'custom_lidar'})
    assert params['subscribers.depth.sensor_frame']=='custom_lidar'


def test_generated_cloud_origin_is_the_generator_base_frame():
    params=launch_parameters({'publish_test_cloud':'true','base_frame':'test_base'})
    assert params['subscribers.depth.sensor_frame']=='test_base'
