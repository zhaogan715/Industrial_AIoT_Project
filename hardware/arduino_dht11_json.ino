#include <DHT.h>
#include <Adafruit_Sensor.h>

// 1. 补充引脚和传感器类型定
#define DHTPIN 2          // 数据引脚接数字2
#define DHTTYPE DHT11     // 传感器型号为DHT11
DHT dht(DHTPIN, DHTTYPE);

// 2. 确保只存在一个setup()函数
void setup() {
  Serial.begin(9600);
  dht.begin();
  Serial.println("DHT11开始工作...");
}

void loop() {
  // 修正'dalay'为'delay'（拼写错误）
  delay(2000);  // 传感器至少需要1秒采样间隔

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // 检查数据是否有效
 if (isnan(humidity) || isnan(temperature)) {
  Serial.println("ERROR");
  delay(1000);
  return;
}

  // 输出温湿度数据
 Serial.print("{\"h\":");
Serial.print(humidity);
Serial.print(",\"t\":");
Serial.print(temperature);
Serial.println("}");
}
