# 新大陆云平台（NLECloud）APIKey 速查

> 记录时间：2026-09-18 ｜ 来源：平台官方说明（用户提供）

## APIKey 是什么

- **APIKey 是调用平台 API 的重要密钥**，每个人通过申请都会获得一个
- 平台 API 调试、应用数据读写、设备控制等接口调用均需携带该密钥

## 相关地址

| 用途 | 地址 |
|---|---|
| 平台首页 | http://www.nlecloud.com |
| APIKey 管理/查看 | http://www.nlecloud.com/my/apikey |
| APIKey 申请 | http://www.nlecloud.com/account/CreateApiKey |

## 关键限制

- ⚠️ **两个月只能申请/修改一次**——申请前务必确认填写信息无误，修改要谨慎
- 密钥属于账号级凭据，不要外泄；泄露后需等两个月窗口才能更换

## 使用场景（GZ038 赛项）

- 模块二云服务应用开发（如 A-13 楼道光控灯）设备数据上报/下发、应用页面数据绑定
- 云端 API 调试（AccessToken 换取、传感器数据读取、执行器控制）均需 APIKey 参与鉴权
