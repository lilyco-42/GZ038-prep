# Python 官方库版（仿照官方例程再写一份）

仿照官方代码重写，两类官方调用方式：

1. **硬件调用库 nle_library**（.pyd，官方 U 盘提供）
   - 连接：`DataBusFactory.newSocketDataBus(ip, port)` / `newSerialDataBus(串口, 波特率)`
   - 采集：`GenericConnector.sendAllInOneTempHum/Body/PM25/AirQuality/Pressure`、`sendGetIlluminance`、`sendGet485Co2Value`
   - 解析：`NLAllInOneSensor`（多合一）、`FourInputConvert`（485 工程值）、`Zigbee`（ZigBee 帧）
   - 控制：`sendRtuWriteData`、`zigbeeControlOne`、`controlRGB`、`sendLedScreenText`
2. **云平台 REST API**（官方 DemoCloud.py 实证写法）
   - `POST /Users/Login` → AccessToken → `GET /devices/{id}/sensors/{tag}` 读实时值

## 文件

| 文件 | 对应赛题 | 说明 |
|---|---|---|
| `nle_quickstart.py` | 通用 | 官方库速查：连接/多合一/485/控制/ZigBee/云平台 各一段 |
| `monitor_system_official.py` | 题6 监控管理系统 | PyQt5（仿官方 DemoCloudWindow）+ 云平台取数（官方实证）+ 摄像头 + 继电器控制 |
| `livingroom_env_official.py` | 题7 客厅环境监控系统升级 | nle_library ZigBee 采集 + 继电器/RGB 控制 + 温度/光照自动联动 + 云平台上报 |

## 运行环境

- 硬件库（nle_library）需 **Python 3.6**（官方 .pyd 编译目标），离线环境见 `知识文档/离线环境快速配置.md`
- 云平台 REST + PyQt5 部分：Python 3.6 / 3.11 均可（PyQt5 5.15.4 已进离线 wheels）
- 无设备运行时：云平台部分可跑通（改配置），硬件部分打印提示不报错

## 使用前必改

把三个文件中的占位配置改为赛场实际值：
- `CLOUD_HOST`（云平台地址，如 http://192.168.0.138）
- `DEVICE_ID` / API_TAG（设备 ID、传感器标识）
- `GATEWAY_IP` / `GATEWAY_PORT`（串口服务器/网关 IP 端口，如 192.168.1.200:8899）
- `ZIGBEE_SERIAL`（ZigBee 继电器短地址，默认 0x141d）

## Qt 界面测试记录（2026-09-17 实测通过）

**测试环境**：`D:\环境部署\运行时\python36`（Python 3.6.8 + PyQt5 5.15.4，全离线环境）

**处理的问题**：Qt 平台插件找不到

```
Could not find the Qt platform plugin "windows" (0xC0000409)
→ 设置环境变量后正常：
QT_QPA_PLATFORM_PLUGIN_PATH=D:\环境部署\运行时\python36\Lib\site-packages\PyQt5\Qt5\plugins\platforms
```

**测试结果**
| 界面 | 结果 |
|---|---|
| 监控管理系统（官方库版） | 界面完整：用户名/密码/项目ID、登录云平台按钮、温度/湿度显示、摄像头画面区、风扇开/关、LED开/关；未登录时数据区显示 `--`，符合预期 |
| 客厅环境监控系统升级（官方库版） | 界面完整：温度/湿度/光照/人体、自动联动说明（温度>30℃开风扇/光照<50开灯）、风扇/LED 控制按钮；无硬件时数据为 `--`，控制台打印"需 py36 + nle_library"提示而非崩溃，容错正常 |

**启动方式**（需带插件路径环境变量，或直接双击同目录 `.bat` 启动器）：
```bat
set QT_QPA_PLATFORM_PLUGIN_PATH=D:\环境部署\运行时\python36\Lib\site-packages\PyQt5\Qt5\plugins\platforms
"D:\环境部署\运行时\python36\python.exe" monitor_system_official.py
```

**说明**
1. 硬件数据（传感器/继电器）需连接真实设备后验证；界面层已全部验证通过
2. 两个脚本均可通过同目录 `start_*.bat` 一键启动（已内置插件路径）
