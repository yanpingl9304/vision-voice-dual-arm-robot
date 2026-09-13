#!/usr/bin/env python3

import os
import launch
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    """
    Drinks Robot Launch 文件 
    包含機器人硬體啟動、視覺偵測與運動控制本體、以及對話節點(Rqt)
    """

    # Conda 環境名稱
    conda_env_name = 'drink_robot'

    # 取得套件目錄
    drinks_robot_pkg_dir = get_package_share_directory('drinks_robot')
    arm_pkg_dir = get_package_share_directory('dual_amm')

    # 引用機器人底層與 GUI launch 檔案路徑
    arm_core_launch_path = os.path.join(arm_pkg_dir, 'launch', 'dual_amm_arm_core.launch.py')
    gui_launch_path = os.path.join(arm_pkg_dir, 'launch', 'dual_amm_gui.launch.py')

    # 配置文件路徑
    params_config = os.path.join(drinks_robot_pkg_dir, 'config', 'drink_robot.yaml')
    arm_params_config = os.path.join(arm_pkg_dir, 'config', 'dual_amm_params.yaml')

    # Launch 參數：是否啟動 GUI
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Whether to launch GUI'
    )

    # 用來繼承 ROS 相關的環境變數給 Conda，避免在虛擬環境中遺失 ROS 路徑
    ros_env = {
        'AMENT_PREFIX_PATH': os.environ.get('AMENT_PREFIX_PATH', ''),
        'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
        'LD_LIBRARY_PATH': os.environ.get('LD_LIBRARY_PATH', ''),
        'ROS_VERSION': os.environ.get('ROS_VERSION', ''),
        'ROS_DISTRO': os.environ.get('ROS_DISTRO', ''),
        'ROS_PYTHON_VERSION': os.environ.get('ROS_PYTHON_VERSION', '')
    }

    # Launch 描述列表
    launch_desc = [
        gui_arg,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([arm_core_launch_path])
        ),
        
        # 機器人本體節點：視覺偵測 + 運動控制
        Node(
            name='drink_robot_node',
            executable='/opt/miniforge3/bin/conda',
            arguments=[
                'run', '-n', conda_env_name, '--no-capture-output',
                'python3', '-m', 'drink_robot.main_task_node'
            ],
            output='screen',
            parameters=[arm_params_config, params_config],
            emulate_tty=True,
            additional_env=ros_env
        ),
    ]

    launch_desc.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([gui_launch_path])
        )
    )

    return LaunchDescription(launch_desc)
