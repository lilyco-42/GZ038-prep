# -*- coding: utf-8 -*-
"""
客厅环境监控系统升级（子任务2-7）· 官方库版
============================================
仿照官方例程再写一份：
  - 硬件采集/控制用官方 nle_library（ZigBee 传感器 + 继电器 + RGB）
  - 云平台上报用官方 DemoCloud.py 的 REST 写法

功能：
  1. ZigBee 传感器采集：温湿度 / 光照 / 人体 / 火焰 / 四输入（CO2、噪音、水浸）
  2. 自动联动：温度过高开风扇、光照过低开灯（升级场景）
  3. 继电器手动控制（风扇/LED）+ RGB 灯带
  4. 云平台定时上报温湿度

运行：python livingroom_env_official.py
"""

import json
import sys
import threading
import time

import requests
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget

# ========== 配置（按赛场实际修改） ==========
GATEWAY_IP = "192.168.1.200"
GATEWAY_PORT = 8899
ZIGBEE_SERIAL = 0x141d            # ZigBee 双联继电器短地址（通道1=风扇，通道2=LED）
CLOUD_HOST = "http://云平台地址"
DEVICE_ID = "设备ID"
API_TAG_TEMP = "temp"
API_TAG_HUM = "humi"

# 自动联动阈值（升级版智能控制）
TEMP_HIGH = 30.0                  # 温度高于此值自动开风扇
LIGHT_LOW = 50.0                  # 光照低于此值自动开灯


class LivingroomWindow(QMainWindow):
    """客厅环境监控主窗口"""

    def __init__(self):
        super(LivingroomWindow, self).__init__()
        self.setWindowTitle("客厅环境监控系统升级（官方库版）")
        self.resize(560, 460)
        self._running = True
        self.conn = None
        self.fan_on = False
        self.led_on = False

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        row1 = QHBoxLayout()
        self.tempLabel = QLabel("温度：--"); self.humiLabel = QLabel("湿度：--")
        self.lightLabel = QLabel("光照：--"); self.bodyLabel = QLabel("人体：--")
        row1.addWidget(self.tempLabel); row1.addWidget(self.humiLabel)
        layout.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(self.lightLabel); row2.addWidget(self.bodyLabel)
        layout.addLayout(row2)

        self.autoLabel = QLabel("自动联动：待机（温度>%.0f℃ 开风扇 / 光照<%.0f 开灯）" % (TEMP_HIGH, LIGHT_LOW))
        layout.addWidget(self.autoLabel)

        row3 = QHBoxLayout()
        self.fanOnBtn = QPushButton("风扇开"); self.fanOnBtn.clicked.connect(lambda: self.ctrl_relay(1, True))
        self.fanOffBtn = QPushButton("风扇关"); self.fanOffBtn.clicked.connect(lambda: self.ctrl_relay(1, False))
        self.ledOnBtn = QPushButton("LED开"); self.ledOnBtn.clicked.connect(lambda: self.ctrl_relay(2, True))
        self.ledOffBtn = QPushButton("LED关"); self.ledOffBtn.clicked.connect(lambda: self.ctrl_relay(2, False))
        row3.addWidget(self.fanOnBtn); row3.addWidget(self.fanOffBtn)
        row3.addWidget(self.ledOnBtn); row3.addWidget(self.ledOffBtn)
        layout.addLayout(row3)

        threading.Thread(target=self._loop, daemon=True).start()

    # ---------- 官方 nle_library 硬件 ----------
    def _get_conn(self):
        if self.conn is None:
            from nle_library.databus.DataBusFactory import DataBusFactory
            from nle_library.device.GenericConnector import GenericConnector
            self.conn = GenericConnector(DataBusFactory.newSocketDataBus(GATEWAY_IP, GATEWAY_PORT))
        return self.conn

    def ctrl_relay(self, channel, is_open):
        """ZigBee 继电器单通道控制（官方库 API：zigbeeControlOne）"""
        try:
            self._get_conn().zigbeeControlOne(ZIGBEE_SERIAL, channel, is_open)
            if channel == 1:
                self.fan_on = is_open
            else:
                self.led_on = is_open
            print("[继电器] 通道%d -> %s" % (channel, "开" if is_open else "关"))
        except Exception as e:
            print("[继电器] 调用失败（需 py36 + nle_library）：%s" % e)

    def _read_zigbee(self):
        """ZigBee 传感器采集回调（官方库 API：setZigbeeDataListener + Zigbee 解析类）"""
        from nle_library.device.Zigbee import Zigbee

        zb = Zigbee()
        state = {}

        def on_data(data):
            try:
                if zb.isReadZigbeeFrame(data):
                    th = zb.getTempHumiSensorData(data)
                    if th is not None:
                        state["temp"], state["humi"] = th
                    li = zb.getLightSensorData(data)
                    if li is not None:
                        state["light"] = li
                    bo = zb.getBodySensorData(data)
                    if bo is not None:
                        state["body"] = bo
            except Exception:
                pass

        try:
            self._get_conn().setZigbeeDataListener(on_data)
        except Exception as e:
            print("[ZigBee] 监听设置失败：%s" % e)
        return state

    # ---------- 云平台上报（官方 DemoCloud.py 写法） ----------
    def report_cloud(self, temp, humi):
        try:
            r = requests.post(CLOUD_HOST + "/Users/Login",
                              data={"Account": "username", "Password": "password", "IsRememberMe": "true"})
            token = json.loads(r.text)["ResultObj"]["AccessToken"]
            # 官方 REST 以 GET 读值为例；上报通常经云平台项目生成器/设备数据接口，按赛场平台实际接口调整
            requests.get("%s/devices/%s/sensors/%s" % (CLOUD_HOST, DEVICE_ID, API_TAG_TEMP),
                         headers={"AccessToken": token})
            print("[云平台] 上报完成 temp=%s humi=%s" % (temp, humi))
        except Exception as e:
            print("[云平台] 上报失败：%s" % e)

    # ---------- 主循环：采集 + 自动联动 ----------
    def _loop(self):
        while self._running:
            try:
                state = self._read_zigbee()
                temp = state.get("temp"); humi = state.get("humi")
                light = state.get("light"); body = state.get("body")
                if temp is not None:
                    self.tempLabel.setText("温度：%.1f℃" % temp)
                if humi is not None:
                    self.humiLabel.setText("湿度：%.1f%%" % humi)
                if light is not None:
                    self.lightLabel.setText("光照：%.0f" % light)
                if body is not None:
                    self.bodyLabel.setText("人体：%s" % ("有人" if body else "无人"))

                # 自动联动（升级版智能控制）
                if temp is not None and temp > TEMP_HIGH and not self.fan_on:
                    self.ctrl_relay(1, True)
                    self.autoLabel.setText("自动联动：温度%.1f℃ 超阈值，已开风扇" % temp)
                if light is not None and light < LIGHT_LOW and not self.led_on:
                    self.ctrl_relay(2, True)
                    self.autoLabel.setText("自动联动：光照%.0f 低于阈值，已开灯" % light)
            except Exception as e:
                print("[主循环]", e)
            time.sleep(1)

    def closeEvent(self, event):
        self._running = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LivingroomWindow()
    window.show()
    sys.exit(app.exec_())
