# GZ038 物联网应用开发 · 备赛资料库

2023 年全国职业院校技能大赛高职组 GZ038「物联网应用开发」赛项备赛资料与全部源代码。
仓库按**赛题模块**组织：每个题目录内同时包含源码项目与当年提交资料。

## 目录结构

| 目录 | 内容 |
|---|---|
| `赛题原题/` | 官方 10 套赛题（第1~10套 docx + 现场截图）+ 真题参考（国赛 1/5/7，含教程/问题/sql） |
| `备赛方案/` | 三份汇总完成方案（Windows 维护 / 全模块 / Android 与 Python 官方库调用） |
| `模块一_Windows维护/` | 模块一（Windows 系统维护）提交截图与脚本（A-*.jpg / sql / txt） |
| `模块二_题4_环境监控/` | 源码：2-4_环境监控（Android）、2-4_远程监控（Android）＋ 提交资料 |
| `模块二_题5_环境监测/` | 源码：2-5_森林火灾监控（Android）、2-5_环境监测系统（Android） |
| `模块二_题6_监控管理/` | 源码：2-6_监控管理系统（Python）、2-6_运输监控（Python）＋ 提交资料 |
| `模块二_题7_智能家居/` | 源码：2-7_客厅环境监控（Python）、2-7_智能商超（Python）＋ 提交资料 |
| `模块二_原型设计/` | 模块二整体原型设计（Axure HTML + .rp） |
| `知识文档/` | nle_library 官方帮助文档、离线环境快速配置、工具与镜像源速查、综合显示屏工具说明 |

## 模块对应关系

| 模块 | 源码项目 | 类型 |
|---|---|---|
| 题4 环境监控 | 2-4_环境监控 / 2-4_远程监控 | Android（Java / Kotlin） |
| 题5 环境监测 | 2-5_森林火灾监控 / 2-5_环境监测系统 | Android（Kotlin / Java） |
| 题6 监控管理 | 2-6_监控管理系统 / 2-6_运输监控 | Python |
| 题7 智能家居 | 2-7_客厅环境监控 / 2-7_智能商超 | Python |

## 环境配套

全离线开发环境（uv 管理 Python + 双环境 + Android 离线素材）见 `知识文档/离线环境快速配置.md`；
官方 Python 调用库 API 参考见 `知识文档/nle_library帮助文档/`。

## Releases（编译成品）

**编译产物（apk/exe/zip 二进制）统一在 [Releases](https://github.com/lilyco-42/GZ038-prep/releases)**（v1.0.0）：
- APK：env-monitor-2-4.apk / remote-monitor-2-4.apk / forest-fire-2-5.apk / env-detect-2-5.apk
- EXE：monitor-mgmt-2-6.exe / livingroom-env-2-7.exe（单文件版）、transport-monitor-2-6-win64.zip / smart-market-2-7-win64.zip（目录版）
- 工具：display-tool-fix.zip（综合显示屏工具修复版）

## 说明

- 仓库为公开仓库，供备赛学习交流；源码已剔除 `__pycache__`、`build/`、`dist/`、`.venv/` 等生成物与本地路径配置（local.properties）。
