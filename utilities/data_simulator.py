import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import random

# --- InfluxDB 配置 ---
BUCKET = "industrial-ai-system"
ORG = "my-org"
TOKEN = "my-super-secret-token"
URL = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("✅ 数据模拟器启动，每5秒向InfluxDB写入一次数据...")

device_statuses = ["Running", "Running", "Running", "Stopped", "Error"]

while True:
    try:
        # 模拟环境数据
        temperature = random.uniform(22.5, 28.5)
        humidity = random.uniform(45.0, 55.0)

        # 模拟设备状态
        status = random.choice(device_statuses)

        # 模拟AI质检结果 (0=OK, 1-9=Defect)
        defect_result = random.choices([0, 3, 5, 8], weights=[90, 5, 3, 2], k=1)[0]

        # 创建数据点
        p_env = influxdb_client.Point("environment").tag("location", "workshop").field("temperature", temperature).field("humidity", humidity)
        p_machine = influxdb_client.Point("machine_status").field("status", status).field("defect_detected", 1 if defect_result > 0 else 0)

        # 写入数据
        write_api.write(bucket=BUCKET, org=ORG, record=[p_env, p_machine])

        print(f"写入数据: Temp={temperature:.1f}, Status='{status}', Defect={defect_result}")

        time.sleep(5) # 每5秒一次
    except KeyboardInterrupt:
        print("\n👋 数据模拟器关闭。")
        break