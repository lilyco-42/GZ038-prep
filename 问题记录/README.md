# 问题记录

备赛过程中遇到并已解决的问题归档（现象 → 原因 → 解决 → 验证）。

| 日期 | 问题 | 状态 | 详录 |
|---|---|---|---|
| 2026-09-17 | Qt 平台插件找不到（Could not find the Qt platform plugin "windows"） | ✅ 已解决 | [2026-09-17_Qt平台插件找不到.md](2026-09-17_Qt平台插件找不到.md) |

## 历史踩坑速查（会话内已解决，未单列文档）

- **gh CLI 传中文参数乱码**（PowerShell 5.1）：中文文件名/标题经 gh 上传会变成 default.* 或乱码 → 产物用 ASCII 文件名、`gh release create --title` 传标题
- **gh release 批量上传失败**：`gh release upload f1 f2 f3` 静默失败 → 改为循环逐个上传
- **git 旧版无 `restore` 子命令**：误删文件用 `git checkout HEAD -- <path>` 恢复；中文路径查看加 `-c core.quotepath=false`
- **uv trampoline 中文路径 bug**：uv 创建的 `Scripts\*.exe` 直接运行报 trampoline failed → 改用 `python.exe -m pip / -m PyInstaller`
- **赛题 docx 损坏**：第 2/4 套 docx Bad CRC-32（media 图片损坏），段落文本可读；第 2/4 套题目文本在文本框内（需解包 document.xml）
- **PS 5.1 向 gh 传参**：含双引号/括号的 jq 表达式被拆参 → 用 `--json` 原始输出或写脚本文件再执行
