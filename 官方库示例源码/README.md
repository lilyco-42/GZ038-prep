# 官方库示例源码（仿照官方例程再写一份）

本目录是**仿照官方代码（库与思路）再写一份**的竞赛源码：

- **Android 版**：仿照官方例程 `DGYJ-fufu/nle-android` 的 `Template/nle_hardware_v1`（GenericConnector 硬件调用）与 `Template/nlecloudII`（云平台 NetWorkBusiness）模板重写，覆盖题4（云服务系统应用开发 / 远程监控应用开发）。
- **Python 版**：仿照新大陆官方 `nle_library`（Python 调用库）重写，覆盖题6（监控管理系统）、题7（客厅环境监控系统升级）。

## 官方代码来源

| 仓库 | 说明 |
|---|---|
| `wyd1520/NewLand-EDU` | 新大陆教育官方资料（物联网实训/竞赛） |
| `DGYJ-fufu/nle-android` | 官方 Android 例程：7 个工程模板 + 全套依赖库（hardware.jar / nle_cloudsdk / TPLink / TTS） |
| `nle_library`（竞赛 U 盘提供） | 官方 Python 调用库（.pyd，含 databus/device/httpHelp/util） |

## 官方库核心 API（本目录代码使用的）

### Android（com.nle.mylibrary.*）
```java
// 连接（TCP 串口服务器 或 串口）
GenericConnector gc = new GenericConnector(
    DataBusFactory.newSocketDataBus(ip, port),          // TCP
    // DataBusFactory.newSerialDataBus(serialName, baud) // 串口
    new ConnectResultListener(){ public void onConnectResult(boolean b){...} });

// 多合一传感器
gc.sendAllInOneGetAddress(new ConnectorListener(){...});  // 取设备地址
gc.sendAllInOneTempHum(address, listener);                // 温湿度
gc.sendAllInOneBody(address, listener);                   // 人体
gc.sendAllInOnePM25(address, listener);                   // PM2.5

// 485 传感器 / 控制
gc.sendGetIlluminance(address, listener);                 // 光照
gc.sendGet485Co2Value(address, listener);                 // CO2
gc.sendRtuWriteData(address, channel, isOpen, listener);  // 继电器/风扇/LED 控制
gc.ZigbeeControl(serialNum, (byte)0x21, null);            // ZigBee 继电器 开

// 云平台（nlecloudII）
NetWorkBusiness nb = new NetWorkBusiness("", "https://api.nlecloud.com/");
nb.signIn(new SignIn(user, pwd), new NCallBack<BaseResponseEntity<User>>(){...});
nb.getSensors(projectID, "temp", new NCallBack<BaseResponseEntity<List<SensorInfo>>>(){...});
nb.control(projectID, "button", 1, new NCallBack<BaseResponseEntity>(){...});
```

### Python（nle_library）
```python
from nle_library.databus.DataBusFactory import DataBusFactory
from nle_library.device.GenericConnector import GenericConnector
from nle_library.device.NLAllInOneSensor import NLAllInOneSensor
from nle_library.common.FourInputConvert import FourInputConvert

conn = GenericConnector(DataBusFactory.newSocketDataBus(ip, port))
conn.sendAllInOneGetAddress(cb)          # 取地址
conn.sendAllInOneTempHum(address, cb)    # 温湿度
conn.sendGetIlluminance(address, cb)     # 光照
conn.sendRtuWriteData(address, ch, True, cb)  # 控制
conn.zigbeeControl(serialNum, True, False)    # ZigBee 继电器
```

## 目录

| 路径 | 内容 |
|---|---|
| `Android/EnvMonitor_官方库/` | 完整 Android 工程：题4 云服务系统应用开发（环境监控）官方库版 |
| `Android/CloudMonitor_官方库/` | 云平台版：远程监控应用开发（NetWorkBusiness 取数/控制） |
| `Python/nle_quickstart.py` | 官方库速查脚本（每类设备一段可运行示例） |
| `Python/monitor_system_official.py` | 题6 监控管理系统 官方库版 |
| `Python/livingroom_env_official.py` | 题7 客厅环境监控系统升级 官方库版 |

> 依赖库（hardware.jar / nle_hardware_v1.jar / nle_library）为官方二进制，不随源码提交，
> 从官方 U 盘资料或 `DGYJ-fufu/nle-android/依赖` 获取后按各 README 放置。
