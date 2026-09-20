import importlib.util
from pathlib import Path

from launch import LaunchContext
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.utilities import perform_substitutions
from ruamel.yaml import YAML


def load_launch(path: Path) -> LaunchDescription:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.generate_launch_description()


def test_semantic_example_launch_descriptions_generate():
    repo_root = Path(__file__).resolve().parents[1]
    launch_files = [
        repo_root / "launch" / "turtlesim_semantic_image_example.launch.py",
        repo_root / "launch" / "turtlesim_semantic_pointcloud_example.launch.py",
    ]

    for launch_file in launch_files:
        description = load_launch(launch_file)
        assert isinstance(description, LaunchDescription)
        assert description.entities


def test_raw_mode_defaults_to_registered_cloud_with_height_layers():
    package_root = Path(__file__).resolve().parents[1]
    config_path = package_root / "config" / "setups" / "raw" / "elevation.yaml"
    config = YAML(typ="safe").load(config_path.read_text(encoding="utf-8"))
    params = config["/elevation_mapping_node"]["ros__parameters"]

    assert params["subscribers"]["depth"]["topic_name"] == "/cloud_registered"
    assert params["publishers"]["elevation_map"]["layers"] == ["elevation", "variance"]

    launch_description = load_launch(package_root / "launch" / "raw_elevation.launch.py")
    topic_argument = next(
        entity
        for entity in launch_description.entities
        if isinstance(entity, DeclareLaunchArgument) and entity.name == "pointcloud_topic"
    )
    default_topic = perform_substitutions(LaunchContext(), topic_argument.default_value)
    assert default_topic == "/cloud_registered"


def test_raw_mode_defaults_to_camera_init_frame():
    package_root = Path(__file__).resolve().parents[1]
    config_path = package_root / "config" / "setups" / "raw" / "elevation.yaml"
    config = YAML(typ="safe").load(config_path.read_text(encoding="utf-8"))
    params = config["/elevation_mapping_node"]["ros__parameters"]

    assert params["map_frame"] == "camera_init"
    assert params["corrected_map_frame"] == "camera_init"

    launch_description = load_launch(package_root / "launch" / "raw_elevation.launch.py")
    frame_argument = next(
        entity
        for entity in launch_description.entities
        if isinstance(entity, DeclareLaunchArgument) and entity.name == "map_frame"
    )
    default_frame = perform_substitutions(LaunchContext(), frame_argument.default_value)
    assert default_frame == "camera_init"
