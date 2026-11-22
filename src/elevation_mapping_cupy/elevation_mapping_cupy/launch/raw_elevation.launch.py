"""Fused elevation + variance without neural traversability; optional test input."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('elevation_mapping_cupy')
    raw = os.path.join(share, 'config', 'setups', 'raw')
    return LaunchDescription([
        DeclareLaunchArgument('publish_test_cloud', default_value='false',
                              description='Publish synthetic cloud + map->base_link TF; use only without real input'),
        DeclareLaunchArgument('launch_rviz', default_value='false'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('pointcloud_topic', default_value='/cloud_registered'),
        DeclareLaunchArgument('pointcloud_sensor_frame', default_value='livox_frame',
                              description='Physical sensor origin, distinct from cloud coordinates'),
        DeclareLaunchArgument('map_frame', default_value='map'),
        DeclareLaunchArgument('base_frame', default_value='base_link'),
        SetLaunchConfiguration('pointcloud_sensor_frame', LaunchConfiguration('base_frame'),
                               condition=IfCondition(LaunchConfiguration('publish_test_cloud'))),
        Node(package='elevation_mapping_cupy', executable='elevation_mapping_node.py',
             name='elevation_mapping_node', output='screen',
             parameters=[os.path.join(share, 'config', 'core', 'core_param.yaml'),
                         os.path.join(raw, 'elevation.yaml'),
                         {'plugin_config_file': os.path.join(raw, 'plugins.yaml'),
                          'use_sim_time': LaunchConfiguration('use_sim_time'),
                          'map_frame': LaunchConfiguration('map_frame'),
                          'corrected_map_frame': LaunchConfiguration('map_frame'),
                          'base_frame': LaunchConfiguration('base_frame'),
                          'subscribers.depth.topic_name': LaunchConfiguration('pointcloud_topic'),
                          'subscribers.depth.sensor_frame': LaunchConfiguration('pointcloud_sensor_frame')}]),
        Node(package='elevation_mapping_cupy', executable='synthetic_pointcloud_tf_publisher.py',
             name='raw_test_cloud', output='screen',
             condition=IfCondition(LaunchConfiguration('publish_test_cloud')),
             parameters=[{'map_frame': LaunchConfiguration('map_frame'),
                          'base_frame': LaunchConfiguration('base_frame'),
                          'pointcloud_topic': LaunchConfiguration('pointcloud_topic'),
                          'trajectory_speed_mps': 0., 'enable_yaw': False,
                          'enable_moving_obstacle': False,
                          'use_sim_time': LaunchConfiguration('use_sim_time')}]),
        Node(package='rviz2', executable='rviz2', output='screen',
             condition=IfCondition(LaunchConfiguration('launch_rviz')),
             arguments=['-d', os.path.join(share, 'rviz', 'raw_elevation.rviz'),
                        '-f', LaunchConfiguration('map_frame')],
             parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]),
    ])
