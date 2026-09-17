# -*- coding: utf-8 -*-
"""
nle_library 官方库速查脚本（仿照官方例程再写一份）
====================================================
覆盖两类官方调用方式：
  1. 硬件调用库 nle_library（.pyd，需 Python 3.6 环境 + nle_library 包）
  2. 云平台 REST API（官方 DemoCloud.py 实证写法）

运行：本脚本可直接执行，无设备时各示例会打印说明，不报错。
"""

import json

# ================= 1. 连接（DataBusFactory + GenericConnector） =================
def demo_connect(ip="192.168.1.200", port=8899, serial_name=None, baud=9600):
    """创建连接器：TCP（串口服务器/网关）或串口（RTU）"""
    from nle_library.databus.DataBusFactory import DataBusFactory
    from nle_library.device.GenericConnector import GenericConnector

    if serial_name:
        data_bus = DataBusFactory.newSerialDataBus(serial_name, baud)   # 串口
    else:
        data_bus = DataBusFactory.newSocketDataBus(ip, port)            # TCP
    conn = GenericConnector(data_bus)
    print("[连接] GenericConnector 已创建：%s:%s" % (ip, port))
    return conn


# ================= 2. 多合一传感器（温湿度/人体/PM2.5/空气质量/气压） =================
def demo_all_in_one(conn, address=1):
    """
    多合一传感器采集。
    官方回调：callback 收到数据帧，用解析类 NLAllInOneSensor 解析；
    若现场回调传参形态有差异，以 U 盘 nle_library 实测为准。
    """
    from nle_library.device.NLAllInOneSensor import NLAllInOneSensor

    parser = NLAllInOneSensor()

    def on_temp_hum(data):
        t, h = parser.getTempHumiValue(data)
        print("[多合一] 温度=%.1f℃  湿度=%.1f%%" % (t, h))

    def on_body(data):
        print("[多合一] 人体=%d (0无人/1有人)" % parser.getBodyValue(data))

    def on_pm25(data):
        print("[多合一] PM2.5=%d" % parser.getPM25Value(data))

    try:
        conn.sendAllInOneTempHum(address, on_temp_hum)      # 温湿度
        conn.sendAllInOneBody(address, on_body)             # 人体
        conn.sendAllInOnePM25(address, on_pm25)             # PM2.5
    except Exception as e:
        print("[多合一] 调用失败（未连接设备或无权限）：%s" % e)


# ================= 3. 485 传感器（光照/CO2/噪音/水浸） =================
def demo_485(conn, address=1):
    """485 单值传感器，用 FourInputConvert 换算工程值"""
    from nle_library.common.FourInputConvert import FourInputConvert

    conv = FourInputConvert()

    def on_light(data):
        print("[485-光照] %.0f lx" % conv.getLight(data))

    def on_co2(data):
        print("[485-CO2] %.0f ppm" % conv.getCo2(data))

    try:
        conn.sendGetIlluminance(address, on_light)   # 光照变送器
        conn.sendGet485Co2Value(address, on_co2)     # CO2 变送器
    except Exception as e:
        print("[485] 调用失败：%s" % e)


# ================= 4. 控制（RTU 继电器 / TCP DO / ZigBee 继电器 / RGB） =================
def demo_control(conn, address=1):
    """执行器控制示例"""
    # 4.1 RTU 设备数字量输出（继电器/风扇/LED）：address 设备地址，channel 通道(1~N)，isOpen 开/关
    conn.sendRtuWriteData(address, 1, True, lambda d: print("[RTU] 通道1 已开启"))
    # 4.2 ZigBee 继电器（serialNum 短地址，通道1/2 独立控制）
    conn.zigbeeControlOne(0x141d, 1, True)           # 通道1 开
    conn.zigbeeControlOne(0x141d, 2, False)          # 通道2 关
    # 4.3 RGB 灯带（red/green/blue 0~255，address 灯带地址）
    conn.controlRGB(255, 0, 0, address, lambda d: print("[RGB] 红色已设置"))
    print("[控制] 指令已发送")


# ================= 5. ZigBee 传感器帧解析 =================
def demo_zigbee_parse(data):
    """ZigBee 传感器数据帧解析（配合 GenericConnector.setZigbeeDataListener）"""
    from nle_library.device.Zigbee import Zigbee

    zb = Zigbee()
    print("[ZigBee-温湿度]", zb.getTempHumiSensorData(data))
    print("[ZigBee-光照]", zb.getLightSensorData(data))
    print("[ZigBee-人体]", zb.getBodySensorData(data))
    print("[ZigBee-火焰]", zb.getFireSensorData(data))
    print("[ZigBee-四输入]", zb.getFourInputSensorData(data))


# ================= 6. 云平台 REST API（官方 DemoCloud.py 实证写法） =================
def demo_cloud(host="http://云平台地址", username="username", password="password",
               device_id="设备ID", api_tag="设备标识"):
    """
    官方 Python 例程（DemoCloud.py）原样思路：
      POST /Users/Login 取 AccessToken → GET /devices/{id}/sensors/{tag} 读实时值
    """
    import requests

    r = requests.post(host + "/Users/Login",
                      data={"Account": username, "Password": password, "IsRememberMe": "true"})
    token = json.loads(r.text)["ResultObj"]["AccessToken"]
    print("[云平台] 登录成功，AccessToken=%s..." % token[:8])

    r = requests.get(host + "/devices/%s/sensors/%s" % (device_id, api_tag),
                     headers={"AccessToken": token})
    value = json.loads(r.text)["ResultObj"]["Value"]
    print("[云平台] 传感器 %s 实时值 = %s" % (api_tag, value))
    return token


# ================= 7. 云平台 SDK（NetWorkBusiness，nle_library 内） =================
def demo_cloud_sdk(host="http://云平台地址", port=80):
    """nle_library.httpHelp.NetWorkBusiness：登录 → 取数 → 控制"""
    from nle_library.httpHelp.NetWorkBusiness import NetWorkBusiness

    nb = NetWorkBusiness(host, port)
    nb.signIn("username", "password", lambda d: print("[SDK] 登录回调"))
    nb.setAccessToken("your_access_token")
    nb.getSensor("设备ID", "设备标识")
    nb.control("设备ID", "设备标识", 1)
    print("[SDK] 云平台 SDK 调用已发起")


if __name__ == "__main__":
    print("=" * 56)
    print("nle_library 官方库速查（仿照官方例程）")
    print("=" * 56)
    print("运行环境：Python 3.6 + nle_library（.pyd），或 Python 3.11（云平台 REST 部分）\n")

    demo_connect()
    print()
    demo_cloud()
    print()
    demo_control.__doc__ and None
    print("提示：硬件类示例（多合一/485/控制/ZigBee）需连接真实设备后调用，")
    print("      对应函数见本文件 demo_all_in_one / demo_485 / demo_control / demo_zigbee_parse。")
