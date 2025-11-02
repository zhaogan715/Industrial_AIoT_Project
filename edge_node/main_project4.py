# -------------------------------------------------------------------
# AI质检 + OPC UA联动 + 环境监测 (主线程GUI版)
# -------------------------------------------------------------------
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import time
import asyncio
from asyncua import Client, ua
import threading
import serial
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import json

# --- 全局配置 ---
RUNNING = True  # 全局停止标志
# --- InfluxDB 配置  ---
INFLUXDB_URL = "http://192.168.191.168:8086"
INFLUXDB_TOKEN = "my-super-secret-token"
INFLUXDB_ORG = "my-org"
INFLUXDB_BUCKET = "industrial-ai-system"
# --- Arduino 串口配置  ---
ARDUINO_PORT = '/dev/ttyACM0' 
# --- OPC UA 配置 ---
OPCUA_URL = "opc.tcp://192.168.191.168:53530/OPCUA/SimulationServer" 
DEFECT_NODE_ID = "ns=3;i=1011"
STATUS_NODE_ID = "ns=3;i=1009"
STOP_NODE_ID = "ns=3;i=1012"
CRITICAL_DEFECT = 5

# --- 线程间共享数据 ---
predicted_label_data = [0]   # AI预测结果

# -------------------------------------------------------------------
# 线程一：环境监测与数据上报 
# (此线程负责Arduino和InfluxDB)
# -------------------------------------------------------------------
def environment_thread_func():
    global RUNNING
    print("✅ (线程1) 环境监测线程启动...")

    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)

    arduino_serial = None
    try:
        arduino_serial = serial.Serial(ARDUINO_PORT, 9600, timeout=2)
        arduino_serial.flush()
        print(f"✅ (线程1) 成功连接到Arduino: {ARDUINO_PORT}")
    except Exception as e:
        print(f"❌ (线程1) 无法连接到Arduino: {e}。将仅上报AI数据。")
        
    while RUNNING:
        try:
            # 1. 从Arduino读取并上报温湿度数据
            if arduino_serial and arduino_serial.in_waiting > 0:
                line = arduino_serial.readline().decode('utf-8').rstrip()
                if line: 
                    try:
                        data = json.loads(line) 
                        p_env = Point("environment").tag("location", "workshop").field("temperature", float(data["temperature"])).field("humidity", float(data["humidity"]))
                        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=p_env)
                        print(f"✅ (线程1) 环境数据已上报: Temp={data['temperature']}, Humidity={data['humidity']}")
                    except json.JSONDecodeError:
                        print(f"❌ (线程1) Arduino数据非JSON格式: {line}")

            # 2. 读取AI质检结果并上报
            current_prediction = predicted_label_data[0]
            p_machine = Point("machine_status").field("defect_detected", 1 if current_prediction > 0 else 0)
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=p_machine)
            
            time.sleep(5) # 每5秒执行一次本循环
        except Exception as e:
            print(f"❌ (线程1) InfluxDB写入错误: {e}")
            time.sleep(5) # 发生错误时等待更长时间

    print("👋 (线程1) 环境监测线程正在关闭...")

# -------------------------------------------------------------------
# 线程二：OPC UA 通信 
# (此线程负责asyncio循环)
# -------------------------------------------------------------------
async def main_opcua_loop():
    print("✅ (线程2) OPC UA子线程启动，正在连接服务器...")
    while RUNNING:
        try: 
            async with Client(url=OPCUA_URL, timeout=4) as client:
                print("✅ (线程2) OPC UA客户端连接成功！")
                defect_node = client.get_node(DEFECT_NODE_ID)
                status_node = client.get_node(STATUS_NODE_ID)
                stop_node = client.get_node(STOP_NODE_ID)

                while RUNNING:
                    current_prediction = predicted_label_data[0]
                    await defect_node.write_value(current_prediction, ua.VariantType.Int32)
                    
                    current_status = await status_node.read_value()
                    
                    if current_prediction == CRITICAL_DEFECT and current_status != "Stopped - Critical Defect":
                        print("🚨 (线程2) 检测到严重缺陷！发送停机指令...")
                        await stop_node.write_value(True, ua.VariantType.Boolean)
                        await status_node.write_value("Stopped - Critical Defect", ua.VariantType.String)
                    elif current_prediction != CRITICAL_DEFECT and current_status != "Running":
                        await status_node.write_value("Running", ua.VariantType.String)

                    await asyncio.sleep(1) # OPC UA通信循环
        except Exception as e: 
            print(f"❌ (线程2) OPC UA连接或通信错误: {e}. 5秒后尝试重连...")
            await asyncio.sleep(5)
    print("👋 (线程2) OPC UA子线程关闭。")

def opcua_thread_func():
    try:
        asyncio.run(main_opcua_loop())
    except Exception as e:
        print(f"❌ (线程2) asyncio循环崩溃: {e}")

# -------------------------------------------------------------------
# 主线程：摄像头、AI识别 与 GUI
# (主线程负责所有OpenCV操作)
# -------------------------------------------------------------------
def main_gui_func():
    global RUNNING
    print("✅ (主线程) OpenCV启动，正在初始化摄像头...")

    interpreter = tflite.Interpreter(model_path="mnist_model_quantized.tflite")
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_shape = input_details[0]['shape']
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ (主线程) 无法打开摄像头！")
        RUNNING = False
        return

    def preprocess_frame(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        side = min(h, w)
        start_y, start_x = (h - side) // 2, (w - side) // 2
        crop_img = gray[start_y:start_y+side, start_x:start_x+side]
        resized = cv2.resize(crop_img, (28, 28), interpolation=cv2.INTER_AREA)
        blurred = cv2.GaussianBlur(resized, (5, 5), 0)
        _, binary_img = cv2.threshold(blurred, 128, 255, cv2.THRESH_BINARY_INV)
        input_data = binary_img.astype('float32') / 255.0
        input_data = input_data.reshape(input_shape)
        return input_data, binary_img

    print("✅ (主线程) 摄像头与模型初始化完毕，开始循环处理...")

    while RUNNING:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
        
        input_data, processed_preview = preprocess_frame(frame)
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        predicted_label = np.argmax(output_data)
        predicted_label_data[0] = int(predicted_label) # 将结果存入共享变量
        
        cv2.putText(frame, f"Prediction: {predicted_label}", (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Camera Feed (Raw)", frame)
        cv2.imshow("Processed Preview (for AI)", cv2.resize(processed_preview, (200, 200)))

        if cv2.waitKey(1) & 0xFF == ord('q'):
            RUNNING = False
            break
            
    print("👋 (主线程) OpenCV正在关闭...")
    cap.release()
    cv2.destroyAllWindows()

# -------------------------------------------------------------------
# 主程序入口
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 项目启动，正在初始化所有线程...")
    
    # 1. 创建并启动“环境监测员”线程
    env_thread = threading.Thread(target=environment_thread_func)
    env_thread.start()

    # 2. 创建并启动“电话接线员”线程
    opcua_thread = threading.Thread(target=opcua_thread_func)
    opcua_thread.start()

    # 3. 在主线程运行GUI
    try:
        main_gui_func()
    except KeyboardInterrupt:
        print("程序被用户中断")
    finally:
        RUNNING = False # 通知所有子线程退出
        env_thread.join()
        opcua_thread.join()
        print("✅ 程序已完全关闭。")