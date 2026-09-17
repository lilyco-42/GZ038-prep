# 远程监控应用开发（子任务2-4）· 官方库版（云平台）

仿照官方例程 `nlecloudII` 模板重写，使用官方云平台 SDK `cn.com.newland.nle_sdk`：
登录 `https://api.nlecloud.com/` → 取传感器实时数据 → 发控制指令。

## 官方库 API（官方模板实证）

| 功能 | API |
|---|---|
| 构造 | `new NetWorkBusiness("", "https://api.nlecloud.com/")` |
| 登录 | `signIn(new SignIn(user, pwd), new NCallBack<BaseResponseEntity<User>>(){ getResultObj().getAccessToken() })` |
| 取数据 | `getSensors(projectID, apiTag, new NCallBack<BaseResponseEntity<List<SensorInfo>>>(){ getResultObj().get(0).getValue() })` |
| 控制 | `control(projectID, apiTag, value, new NCallBack<BaseResponseEntity>(){...})` |

## 依赖放置（官方二进制，不入库）

复制官方 `依赖/nle_cloudsdk/nle_cloudsdk_v1.jar` 到 `app/libs/`，并在 `app/build.gradle.kts` 中：
```kotlin
implementation(files("libs\\nle_cloudsdk_v1.jar"))
```
工程骨架同 `../EnvMonitor_官方库`（拷贝 settings/build.gradle.kts/gradle.properties/gradle/libs.versions.toml 后改 namespace 为 `com.newland.cloudmonitor`）。

## 使用

填入云平台用户名/密码/项目ID → 登录 → 查询（apiTag 可按项目修改，如 temp/hum/light）→ 控制。
