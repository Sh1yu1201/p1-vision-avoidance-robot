# ROS 2 功能包目录

本目录预留给项目的 ROS 2 功能包，建议按下面的方式划分：

```
ros2_ws/src/
├── p1_vision_bringup/     # 启动文件：摄像头、NPU 推理节点、参数配置
├── p1_vision_perception/  # 检测、深度估计、高度图生成节点
├── p1_semantic_decision/  # VLM 事件触发与决策节点
└── p1_description/        # 机器人 URDF / xacro 描述与仿真模型
```

编译与运行：

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch p1_vision_bringup vision_only_demo.launch.py
```

说明：底盘仿真可基于开源项目 OOMWOO 的 ROS 2 描述与 Gazebo 环境（github.com/makerspet/oomwoo-one）搭建，
本目录只保留我们自己的适配包。
