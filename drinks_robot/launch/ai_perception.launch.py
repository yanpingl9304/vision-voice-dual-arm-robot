#!/usr/bin/env python3
"""ai_perception.launch.py - Launch the robot node and voice interface (Conda required).

Starts the arm hardware core, the main drink robot task node,
and the voice/AI interface node. All heavy AI nodes run via conda.

Usage:
    conda activate drink_robot
    ros2 launch drinks_robot ai_perception.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

CONDA_ENV = 'drink_robot'
CONDA_BIN = '/opt/miniforge3/bin/conda'


def generate_launch_description():
    drinks_robot_pkg_dir = get_package_share_directory('drinks_robot')
    arm_pkg_dir = get_package_share_directory('dual_amm')

    arm_core_launch = os.path.join(arm_pkg_dir, 'launch', 'dual_amm_arm_core.launch.py')
    params_config = os.path.join(drinks_robot_pkg_dir, 'config', 'drink_robot.yaml')
    arm_params_config = os.path.join(arm_pkg_dir, 'config', 'dual_amm_params.yaml')

    ros_env = {
        'AMENT_PREFIX_PATH': os.environ.get('AMENT_PREFIX_PATH', ''),
        'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
        'LD_LIBRARY_PATH': os.environ.get('LD_LIBRARY_PATH', ''),
        'ROS_VERSION': os.environ.get('ROS_VERSION', ''),
        'ROS_DISTRO': os.environ.get('ROS_DISTRO', ''),
        'ROS_PYTHON_VERSION': os.environ.get('ROS_PYTHON_VERSION', ''),
    }

    return LaunchDescription([
        # Arm hardware core
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([arm_core_launch])
        ),

        # Main drink robot task node (behavior tree + arm control)
        Node(
            name='drink_robot_node',
            executable=CONDA_BIN,
            arguments=[
                'run', '-n', CONDA_ENV, '--no-capture-output',
                'python3', '-m', 'drink_robot.main_task_node',
            ],
            output='screen',
            parameters=[arm_params_config, params_config],
            emulate_tty=True,
            additional_env=ros_env,
        ),

        # Voice & AI interface node
        Node(
            name='voice_interface_node',
            executable=CONDA_BIN,
            arguments=[
                'run', '-n', CONDA_ENV, '--no-capture-output',
                'python3', '-m', 'drink_robot.hmi.voice_interface_node',
            ],
            output='screen',
            emulate_tty=True,
            additional_env=ros_env,
        ),
    ])
