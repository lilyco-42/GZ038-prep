# 环境监控（云服务系统应用开发 - 子任务2-4）· 官方库版

仿照官方例程 `DGYJ-fufu/nle-android` 的 `Template/nle_hardware_v1`（AllInOne + ZigBee 模板）重写，
使用官方硬件调用库 `com.nle.mylibrary.*` 实现：TCP 连接 → 多合一传感器采集 → ZigBee 传感器帧解析 → 继电器控制（风扇 / LED）。

## 官方库 API（本工程使用）

| 功能 | API（官方模板实证） |
|---|---|
| TCP 连接 | `DataBusFactory.newSocketDataBus(ip, port)` |
| 连接回调 | `new GenericConnector(dataBus, new ConnectResultListener(){ onConnectResult(boolean) })` |
| ZigBee 帧解析 | `dataBus.setReciveDataListener(new ReciveData(){ getReciveData(byte[]) })` + `new ZigBee3(bytes)` + `ZigBeeSensorType.*.getCode()` |
| 四输入换算 | `FourChannelValConvert.getTemperature()/getHumidity()/getLight()/getCo2()` |
| 多合一地址 | `sendAllInOneGetAddress()` / `getAllInOneGetAddress()` |
| 多合一采集 | `sendAllInOneTempHum/Body/PM25/AirQuality/Pressure` + `getAllInOneTemp/Hum/Body/Pm25/AirQuality/Pressure` |
| 继电器控制 | `ZigbeeControl(serialNum, cmd, null)`：双联 0x11全开 0x22全关 0x21一开二关 0x12一关二开 |
| 断开 | `genericConnector.stopConnect()` |

## 依赖放置（官方二进制，不入库）

1. 从官方 U 盘「竞赛资料」或官方例程 `依赖/jar包及说明文档_modbus4150_4017_zigbee_rfid_led/libs/hardware.jar` 获取 `nle_hardware_v1.jar`
2. 复制到 `app/libs/nle_hardware_v1.jar`（同时放入 `gson-2.8.1.jar`，与官方模板一致）
3. `app/libs/` 下需含串口 so 库：`arm64-v8a / armeabi-v7a / x86 / x86_64` 各 `libserial_port.so`（官方依赖目录提供）

## 赛场参数

- 串口服务器 TCP 模式：`192.168.1.200:8899`（数据端口，界面可改）
- ZigBee 双联继电器短地址 `0x141d`：通道1=风扇、通道2=LED（按实际工位修改 `RELAY_SERIAL`）
- 若串口服务器为 8899/8888 双端口（数据/控制分离），控制通道可再建一个 `DataBusFactory.newSocketDataBus(ip, 8888)`
  通过 `dataBus.sendProtocol(Modbus帧)` 下发，或直接改用官方网关。

## 运行

Android Studio 打开工程 → 等待 Gradle 同步 → 放入官方 jar 后 Build → 安装到物联网应用开发终端 → 输入 IP/端口 → 连接 → 查看数据并控制。
