# -------------------------------------------------------------------
# 这是一个完整的“训练+转换”一体化脚本
# -------------------------------------------------------------------
import tensorflow as tf
import numpy as np

# --- 1. 数据准备  ---
print("✅ 步骤 1: 正在加载和预处理MNIST数据集...")
(x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

# 归一化和形状调整
x_train = x_train.astype("float32") / 255.0
x_test = x_test.astype("float32") / 255.0
x_train = x_train.reshape(-1, 784)
x_test = x_test.reshape(-1, 784)
print("数据集准备完毕！")

# --- 2. 定义并编译模型  ---
print("\n✅ 步骤 2: 正在定义Keras模型...")
model = tf.keras.Sequential([
    tf.keras.layers.Dense(128, activation='relu', input_shape=(784,)),
    tf.keras.layers.Dense(10, activation='softmax')
])
model.summary() # 打印模型结构

print("\n正在编译模型...")
model.compile(
    optimizer='adam',
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=False),
    metrics=['accuracy']
)
print("模型编译完毕！")

# --- 3. 训练模型 (来自你的源代码) ---
print("\n✅ 步骤 3: 开始训练模型 (epochs=10)...")
model.fit(
    x_train, 
    y_train,
    epochs=10,
    batch_size=32,
    validation_split=0.1
)
print("模型训练完毕！")

# --- 4. 评估并保存H5模型  ---
print("\n✅ 步骤 4: 正在评估模型...")
loss, acc = model.evaluate(x_test, y_test, verbose=2)
print(f"在测试集上的准确率: {acc:.4f}")

H5_MODEL_PATH = "mnist_model.h5"
print(f"\n正在将训练好的模型保存到: {H5_MODEL_PATH}...")
model.save(H5_MODEL_PATH)
print("H5模型保存成功！")

# --- 5. 使用“具体函数”方法将模型转换为TFLite ---
# ------------------------------------------------------
print("\n✅ 步骤 5: 开始将模型转换为TFLite格式...")
TFLITE_MODEL_PATH = "mnist_model_quantized.tflite"

try:
    # 从刚刚训练好的模型对象中获取具体函数
    full_model = tf.function(lambda x: model(x))
    input_spec = tf.TensorSpec(shape=[1, 784], dtype=tf.float32)
    concrete_func = full_model.get_concrete_function(input_spec)

    # 从具体函数初始化转换器
    print("    -> 正在初始化TFLite转换器...")
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])

    # 应用量化
    print("    -> 正在应用默认量化...")
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    # 执行转换
    print("    -> 正在执行转换...")
    tflite_model = converter.convert()

    # 保存TFLite模型
    with open(TFLITE_MODEL_PATH, 'wb') as f:
        f.write(tflite_model)

    print(f"\n🎉🎉🎉 恭喜！TFLite模型转换成功并已保存到: {TFLITE_MODEL_PATH}")

except Exception as e:
    print(f"\n❌ 错误: TFLite转换失败: {e}")