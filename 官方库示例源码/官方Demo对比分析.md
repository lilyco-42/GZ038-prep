# 官方 Demo 实现 vs 我们"再写一份"实现 · 对比分析

- 日期：2026-09-17
- 范围：Android（官方 nle-android 模板 ↔ `Android/EnvMonitor_官方库`、`Android/CloudMonitor_官方库`）、Python（官方 NewLand-EDU Demo ↔ `Python/` 三个脚本）

## 1. 官方仓库检索结果（gh search）

| 仓库 | 说明 | 语言 |
|---|---|---|
| `wyd1520/NewLand-EDU` | 新大陆教育官方资料（物联网实训/竞赛，Python 官方 Demo 所在） | Python |
| `DGYJ-fufu/nle-android` | 基于 NewLand-EDU 的 Android 例程（7 个工程模板 + 全套依赖库） | Java/Kotlin |
| `DGYJ-fufu/nle-stm32` | 基于 NewLand-EDU 的 STM32 例程 | C |

官方 Demo 取用：
- Android：`nle-android/Template/nle_hardware_v1/AllInOne`（多合一采集）、`ZigBee`（帧解析+继电器）、`nlecloudII`（云平台）
- Python：`NewLand-EDU/物联网实训/物联网应用开发/Python环境安装/Demo/DemoCloud.py`（云平台 REST）、`DemoCloudWindow.py`（PyQt5 界面）

## 2. 官方 Demo 核心实现（基线）

### 2.1 Android 官方模板（com.nle.mylibrary.*）

| 模板 | 实现要点 |
|---|---|
| AllInOne | `GenericConnector(DataBusFactory.newSocketDataBus(ip,port))` 连接 → `sendAllInOneGetAddress` 取地址 → 单线程轮询 `sendAllInOneTempHum/Body/PM25/AirQuality/Pressure` → `handler.post` 更新 UI；连接/断开用 `ConnectResultListener` + `stopConnect()` |
| ZigBee | `dataBus.setReciveDataListener` 收帧 → `new ZigBee3(bytes)` 按 `ZigBeeSensorType` 分支解析（温湿度/光照/人体/火焰/四输入，`FourChannelValConvert` 换算）→ `ZigbeeControl(serialNum, 0x21/0x22, null)` 控制继电器 |
| nlecloudII | `NetWorkBusiness("", "https://api.nlecloud.com/")` → `signIn(new SignIn(user,pwd))` 拿 AccessToken → `getSensors(projectID, apiTag)` 读值 → `control(projectID, apiTag, value)` 控制 |

### 2.2 Python 官方 Demo（NewLand-EDU）

| Demo | 实现要点 |
|---|---|
| DemoCloud.py | REST 直连：`POST /Users/Login` 取 AccessToken → `GET /devices/{id}/sensors/{tag}` 读实时值（纯 requests） |
| DemoCloudWindow.py | 同上 + PyQt5 界面（登录按钮 → 读温度/湿度 → QLabel 显示） |

## 3. Android 对比

| 维度 | 官方 AllInOne 模板 | 我们的 EnvMonitor_官方库 | 差异说明 |
|---|---|---|---|
| 连接 | `newSocketDataBus(ip,port)` + `GenericConnector` + `ConnectResultListener` | 完全相同 | 沿用官方库思路 |
| 取地址 | `sendAllInOneGetAddress` → `getAllInOneGetAddress` | 相同 | — |
| 采集 | 多合一 6 项（temp/hum/body/pm25/air/pressure） | 多合一 + ZigBee 帧解析（温湿度/光照/人体/火焰/四输入） | 我们合并了两模板能力，覆盖光照/火焰（环境监控场景） |
| 控制 | 官方 ZigBee 模板 `ZigbeeControl(0x141d, cmd)` | 双联继电器状态机：风扇/LED 两按钮 → `0x11/0x22/0x21/0x12` 组合 | 官方 demo 只演示"开/关"单按钮，我们做了双通道互斥状态机 |
| UI | 官方 demo 固定控件 + 多线程 tag 顺序采集 | 简化布局 + `updateSensor` 统一刷新 + 控制按钮状态显示 | 官方 tag 顺序锁较繁琐，我们改为轮询间隔 |
| 容错 | 连接失败置空 + Toast | 相同 | — |
| 扩展 | — | 485 光照/CO2 接入点、云平台上报预留（README 注明） | 面向赛题场景扩展 |

| 维度 | 官方 nlecloudII 模板 | 我们的 CloudMonitor_官方库 | 差异说明 |
|---|---|---|---|
| 登录 | `signIn` + `NCallBack` 内重建 `NetWorkBusiness(token)` | 相同 + 失败判空提示 | 补了官方 demo 缺失的错误处理 |
| 取数 | `getSensors(projectID, "temp")` 仅 Log | 显示到界面 + 单位拼接 | 面向演示 |
| 控制 | `control(projectID, "button", 1)` 空回调 | ON/OFF 双按钮 + Toast 反馈 | 面向演示 |

## 4. Python 对比

| 维度 | 官方 DemoCloudWindow.py | 我们的 monitor_system_official.py | 差异说明 |
|---|---|---|---|
| 界面框架 | PyQt5 `QMainWindow` 手工布局 | PyQt5 `QMainWindow` + 布局管理器（QVBox/QHBox） | 框架一致，布局更规范 |
| 云平台 | 登录 → 读温度/湿度（REST 实证写法） | 相同 + 轮询线程定时刷新 | 官方是点按钮读一次，我们加了自动刷新 |
| 扩展 | 仅 2 个传感器标签 | + 摄像头画面（requests 快照线程）+ 风扇/LED 控制（nle_library） | 面向题6 监控管理场景 |
| 容错 | 无 | 无 token 显示 `--`、摄像头失败静默、硬件缺库提示不崩溃 | 补了官方 demo 缺失的容错 |

| 维度 | 官方 DemoCloud.py | 我们的 livingroom_env_official.py / nle_quickstart.py | 差异说明 |
|---|---|---|---|
| 硬件 | 无（官方 Python 无硬件 demo，仅云平台 REST） | nle_library 硬件采集（ZigBee 温湿度/光照/人体/火焰/四输入）+ 继电器/RGB 控制 + 自动联动 | 官方 Python 侧缺失硬件例程，我们补全（API 取自 nle_library 帮助文档实证） |
| 云平台 | `GET /devices/{id}/sensors/{tag}` | 相同 REST 思路 + 上报 | 沿用官方写法 |
| 速查 | — | nle_quickstart.py 每类设备一段 | 备赛速查用 |

## 5. 结论

1. **思路一致**：所有"再写一份"实现均严格采用官方库/官方 REST 调用（`GenericConnector`、`DataBusFactory`、`ZigBee3`、`NetWorkBusiness`、`/Users/Login`），非自写协议；官方模板的"连接→取地址→轮询采集→回调更新 UI"骨架完整保留。
2. **官方缺什么我们补什么**：
   - Python 官方无硬件 demo（只有云平台 REST）→ 我们用 nle_library 帮助文档 API 补齐硬件采集/控制
   - 官方 demo 容错弱（空回调、无错误处理）→ 全部补了失败提示/判空/缺库降级
   - 官方控制 demo 只有单按钮 → 我们做了双通道继电器状态机（风扇/LED）
3. **官方有而我们简化**：官方 AllInOne 的"tag 顺序锁"多线程采集较繁琐，我们改为固定间隔轮询（同库 API，行为等价，代码更短）。
4. **竞赛建议**：赛场上优先用"再写一份"版本（容错 + 场景完整）；若裁判要求贴近官方模板结构，官方模板原样也可编译运行。
