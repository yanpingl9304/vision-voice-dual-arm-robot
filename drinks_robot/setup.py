from setuptools import find_packages, setup
from glob import glob

package_name = 'drinks_robot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'plugin.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/resource', glob('resource/*.*')),
        ('share/' + package_name + '/resource/WakeWord', glob('resource/WakeWord/*.*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ncku_csie_rl',
    maintainer_email='94117313+TienYuWu@users.noreply.github.com',
    description='Dual-arm drink service robot node with container ArUco and cup detection pipeline.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'drink_robot_node = drinks_robot.main_task_node:main',
            'voice_interface_node = drinks_robot.hmi.voice_interface_node:main',
        ],
    },
)
