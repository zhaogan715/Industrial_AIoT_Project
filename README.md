<img width="659" height="415" alt="image" src="https://github.com/user-attachments/assets/c3cba3da-1d52-40a7-9624-7e94480760fe" />Markdown

# 工业AI质检与数字孪生系统 v1.0

![Project Status](https://img.shields.io/badge/status-complete-green)
![Python Version](https://img.shields.io/badge/python-3.11-blue)
![Framework](https://img.shields.io/badge/framework-TensorFlow%20Lite%20%7C%20asyncua%20%7C%20Grafana-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

本项目是一个基于边缘计算的工业物联网（AIoT）解决方案，旨在模拟一个现代智能制造场景。系统实现了从 **边缘AI视觉感知**、**M2M工业协议控制**，到 **云端时序数据可视化** 的端到端全数据链路。

它展示了一个简单的AI任务（手写数字识别）背后，所需要搭建的**健壮、高并发、多协议的工业级系统架构**。

---

###  演示视频 (Demo)


【工业ai质检与数字孪生系统演示——GitHub/zhaogan-哔哩哔哩】 https://b23.tv/94bufkt

---

###  核心功能 (Features)

* **实时AI边缘推理**: 在树莓派边缘节点上，使用TensorFlow Lite和OpenCV，对实时视频流进行AI质检（<100ms）。
* **双重视觉调试**: 同时显示“原始视频流”和“AI预处理特征图”（28x28黑白图像），实时监控AI的“所见”。
* **工业M2M联动**: AI识别结果（如“缺陷品”）通过**OPC UA**协议，实时触发模拟产线设备（Prosys服务器）的自动停机指令。
* **数字孪生仪表盘**: 在Grafana中构建的实时监控中心，通过**Flux**语言从InfluxDB拉取数据，极大程度还原物理系统的数字镜像。
* **多线程高并发架构**: 解决了Python的`asyncio`（异步I/O）与`cv2.imshow`（同步GUI）的冲突，实现了三个线程并行工作，互不阻塞。
* **全链路环境遥测**: 通过Arduino和`pyserial`库，将实时的温湿度遥测数据上报至InfluxDB，与AI质检结果在同一平台归档。

---

### 🏗️ 项目架构 (Project Architecture)

本项目的架构设计清晰地分离了后端服务、边缘计算和硬件感知，核心`main_project.py`采用三线程模型解耦了GUI与I/O任务。
```
+--------------------------------------------------------------------------------+
| 主电脑（监控层 / 模拟工厂） |
| +------------------------------------------------------------------------------+
| | [ Docker ] [ Prosys OPC UA Server ] |
| | [ Grafana ] (可视化) <-(Flux 查询)-> [ InfluxDB ] |
| | DeviceStatus (Node) <-(读写)-> [ AI状态面板 ] (时序数据库) |
| | TriggerStop (Node) [ 温湿度曲线 ] |
| | (HTTP 写入, 每5秒) |
| +------------------------------------------------------------------------------+
| (OPC UA 读写, 每1秒) |
| (网络层: Wi-Fi / 以太网) |
| +------------------------------------------------------------------------------+
| 树莓派 4B （边缘计算层） |
| +------------------------------------------------------------------------------+
| | main_project.py |
| | ├── 主线程：GUI 与系统调度 |
| | ├── 子线程1：环境监测 |
| | ├── 子线程2：OPC UA 通信 |
| | |
| | OpenCV & AI |
| | Arduino (Serial /dev/...) |
| | asyncio (Asyncio Loop) |
| | GUI（阻塞显示） + InfluxDB Client（高I/O 网络） |
| | [ AI结果 ] -> (共享变量) -> [ 上报 InfluxDB ] -> [ 写入 OPC UA ] |
| +------------------------------------------------------------------------------+
| ^ (USB) / (UART) |
| +------------------------------------------------------------------------------+
| 感知层：Arduino Uno + DHT11 + USB 摄像头 |
+--------------------------------------------------------------------------------+
```
---

### 🔧 技术栈 (Technology Stack)

* **边缘计算**: Python 3.11, Raspberry Pi 4B
* **AI 框 架**: TensorFlow Lite (`tflite-runtime`), OpenCV, NumPy
* **工业通信**: OPC UA (`asyncua` 库)
* **数 据 后 端**: Docker, InfluxDB v2.7, Grafana
* **数 据 查 询**: Flux Language
* **硬 件 通 信**: `pyserial`, `Arduino (C++)`, `ArduinoJson`
* **并 发 编 程**: `threading` (多线程), `asyncio` (异步)

---

### 🧩 核心挑战与解决方案

**挑战**: 在单一Python脚本中，同时运行 `cv2.imshow` (GUI) 和 `asyncio` (网络I/O)。

* **问题**: `cv2.imshow` 及其 `cv2.waitKey` 是**同步阻塞**操作，必须在主线程中运行。而 `asyncio.run()` 也是一个**阻塞**操作，它会启动自己的事件循环来管理异步I/O（如OPC UA通信）。当它们在同一个线程中时，两者会互相“冻结”，导致GUI卡死或网络超时。
* **解决方案**: **架构重构为三线程模型**。
    1.  **主线程**: 专门负责`OpenCV`的GUI循环 (`main_gui_func`)，确保窗口实时刷新。
    2.  **子线程 1**: 专门运行`asyncio`事件循环 (`opcua_thread_func`)，在后台高并发地处理OPC UA通信。
    3.  **子线程 2**: 专门运行`pyserial`和`influxdb-client` (`environment_thread_func`)，在后台处理硬件串口的阻塞读取和网络上报。
    4.  **线程通信**: 使用线程安全的全局变量（如`RUNNING`标志和`predicted_label_data`列表）来协调所有线程的启动、数据共享和优雅退出。

---

### 💻 硬件需求

* 树莓派4B（已安装64位Raspberry Pi OS）
* 免驱动的USB摄像头
* Arduino Uno
* DHT11 温湿度传感器
* 杜邦线、面包板、USB数据线
* 一台用于运行后端的PC（Windows/macOS/Linux）

---

### ⚙️ 快速上手 (Installation & Usage)

#### 1. 后端服务 (在主电脑上)

1.  安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。
2.  安装 [Prosys OPC UA Simulation Server](https://www.prosysopc.com/products/opc-ua-simulation-server/)。
3.  在`backend_services/`目录中，创建 `docker-compose.yml` 。
4.  在Prosys中，创建好你的模拟节点（`DeviceStatus`, `TriggerStop`, `DefectType`），并**右键复制它们的NodeId**。
5.  启动服务:
    ```bash
    cd backend_services
    docker-compose up -d
    ```

#### 2. 硬件 (Arduino)

1.  在Arduino IDE中，安装 `ArduinoJson` 库。
2.  烧录 `hardware/arduino_dht11_json.ino` 固件到Arduino Uno。

#### 3. 边缘节点 (树莓派)

1.  将`edge_node/`目录下的所有文件传输到树莓派的`/home/pi`目录。
2.  将Arduino和USB摄像头连接到树莓派。
3.  打开PuTTY终端，创建并激活虚拟环境：
    ```bash
    python3 -m venv tflite-env
    source tflite-env/bin/activate
    ```
4.  安装所有依赖：
    ```bash
    # AI 依赖
    pip install "tflite-runtime==2.14.0" "numpy==1.26.4" opencv-python
    
    # IoT 依赖
    pip install asyncua pyserial influxdb-client
    ```
5.  **修改脚本配置 (最关键一步)**:
    * 打开 `main_project.py`。
    * 将 `INFLUXDB_URL` 和 `OPCUA_URL` 中的IP地址，**替换为自己主电脑的真实IP地址**。
    * 将 `DEFECT_NODE_ID`, `STATUS_NODE_ID`, `STOP_NODE_ID` **替换为自己从Prosys复制的精确NodeId**。
    * 确认 `ARDUINO_PORT` (如 `/dev/ttyACM0`) 是否正确。

#### 4. 启动系统

1.  通过 **X11转发** (如 MobaXterm 或 `ssh -X`) 登录的，或者给树莓派外接了显示器。
2.  在已激活虚拟环境的终端中，运行：
    ```bash
    cd /home/pi/edge_node
    python main_project.py
    ```
3.  系统将启动，同时弹出两个摄像头窗口，终端开始打印日志，Grafana仪表盘开始接收数据。

---

### 📜 许可证 (License)


本项目采用 MIT 许可证。





