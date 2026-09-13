#!/usr/bin/env python3
"""ui_core.launch.py - Launch only the RQT GUI (no Conda required).

The rqt_chat_plugin has been stripped of all AI/voice dependencies,
so it runs in any standard ROS 2 environment.

Usage:
    ros2 launch drinks_robot ui_core.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            name='rqt_chat_ui',
            executable='rqt',
            arguments=['--force-discover'],
            output='screen',
            emulate_tty=True,
        ),
    ])
