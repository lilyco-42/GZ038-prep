GZ038 第9套 子任务2-6  气象系统 (Python)
=========================================================

文件:
  weather.py     主程序: LED大屏显示5个传感器, 每10秒刷新
  nle_cloud.py  云服务客户端(标准库urllib, 含demo模拟降级)
  config.json   配置: 云服务地址/账号/刷新周期/传感器标识

运行: python weather.py
依赖: 仅 Python 标准库(tkinter/urllib/json), 无需 requests/openpyxl。

显示:
  黑底绿字 LED 屏, 每 10 秒显示一行:
  温度 xx，湿度 xx，光照 xx，CO2 xx，噪音 xx

传感器标识(config.json 中可改):
  温度=m_temp  湿度=m_hum  光照=m_light  CO2=m_co2  噪音=m_noise

模式:
  mode=cloud  真实连云服务(默认 192.168.0.138)
  mode=demo   云服务不可达时自动用模拟数据, 保证程序可运行验收

打包: 气象系统.rar -> D:\提交资料\模块二\题6
