# -*- coding: utf-8 -*-
"""
监控管理系统（子任务2-6）· 官方库版
====================================
仿照官方例程再写一份：
  - 界面框架仿官方 DemoCloudWindow.py（PyQt5）
  - 云平台取数/登录仿官方 DemoCloud.py（REST 实证写法）
  - 硬件采集与控制用官方 nle_library（.pyd 硬件库）

功能：云平台登录 → 实时显示温度/湿度 → 摄像头画面 → 风扇/继电器控制
运行：python monitor_system_official.py
"""

import json
import sys
import threading
import time

import requests
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QWidget

# ========== 配置（按赛场实际修改） ==========
CLOUD_HOST = "http://云平台地址"          # 云平台地址（如 http://192.168.0.138）
DEVICE_ID = "设备ID"                      # 云平台设备 ID
API_TAG_TEMP = "temp"                     # 温度 设备标识
API_TAG_HUM = "humi"                      # 湿度 设备标识
CAMERA_SNAPSHOT = "http://192.168.1.100/snapshot.jpg"   # 摄像头快照地址


class MonitorWindow(QMainWindow):
    """监控管理系统主窗口（仿官方 DemoCloudWindow 的 PyQt5 布局思路）"""

    def __init__(self):
        super(MonitorWindow, self).__init__()
        self.setWindowTitle("监控管理系统（官方库版）")
        self.resize(720, 560)
        self.token = ""
        self._running = True

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 登录行
        row_login = QHBoxLayout()
        self.userEdit = QLineEdit(); self.userEdit.setPlaceholderText("用户名")
        self.pwdEdit = QLineEdit(); self.pwdEdit.setPlaceholderText("密码"); self.pwdEdit.setEchoMode(QLineEdit.Password)
        self.loginBtn = QPushButton("登录云平台"); self.loginBtn.clicked.connect(self.on_login)
        row_login.addWidget(self.userEdit); row_login.addWidget(self.pwdEdit); row_login.addWidget(self.loginBtn)
        layout.addLayout(row_login)

        # 数据行
        row_data = QHBoxLayout()
        self.tempLabel = QLabel("温度：--"); self.humiLabel = QLabel("湿度：--")
        row_data.addWidget(self.tempLabel); row_data.addWidget(self.humiLabel)
        layout.addLayout(row_data)

        # 摄像头画面
        self.cameraLabel = QLabel("摄像头画面"); self.cameraLabel.setFixedHeight(320)
        self.cameraLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.cameraLabel.setStyleSheet("background:#222;color:#aaa;")
        layout.addWidget(self.cameraLabel)

        # 控制行
        row_ctrl = QHBoxLayout()
        self.fanOnBtn = QPushButton("风扇开"); self.fanOnBtn.clicked.connect(lambda: self.on_control(1, True))
        self.fanOffBtn = QPushButton("风扇关"); self.fanOffBtn.clicked.connect(lambda: self.on_control(1, False))
        self.ledOnBtn = QPushButton("LED开"); self.ledOnBtn.clicked.connect(lambda: self.on_control(2, True))
        self.ledOffBtn = QPushButton("LED关"); self.ledOffBtn.clicked.connect(lambda: self.on_control(2, False))
        row_ctrl.addWidget(self.fanOnBtn); row_ctrl.addWidget(self.fanOffBtn)
        row_ctrl.addWidget(self.ledOnBtn); row_ctrl.addWidget(self.ledOffBtn)
        layout.addLayout(row_ctrl)

        # 后台线程：摄像头刷新 + 数据轮询
        threading.Thread(target=self._camera_loop, daemon=True).start()
        threading.Thread(target=self._data_loop, daemon=True).start()

    # ---------- 云平台（官方 DemoCloud.py 实证写法） ----------
    def on_login(self):
        r = requests.post(CLOUD_HOST + "/Users/Login",
                          data={"Account": self.userEdit.text(),
                                "Password": self.pwdEdit.text(),
                                "IsRememberMe": "true"})
        self.token = json.loads(r.text)["ResultObj"]["AccessToken"]
        self.loginBtn.setText("已登录")
        self.setWindowTitle("监控管理系统（官方库版）— 已登录")

    def read_sensor(self, api_tag):
        """官方 DemoCloud.py 原样：GET /devices/{id}/sensors/{tag}"""
        if not self.token:
            return "--"
        try:
            r = requests.get("%s/devices/%s/sensors/%s" % (CLOUD_HOST, DEVICE_ID, api_tag),
                             headers={"AccessToken": self.token}, timeout=3)
            return str(json.loads(r.text)["ResultObj"]["Value"])
        except Exception:
            return "--"

    # ---------- 硬件（官方 nle_library） ----------
    def on_control(self, channel, is_open):
        """继电器控制：RTU 输出或 ZigBee 继电器（官方库 API）"""
        try:
            from nle_library.databus.DataBusFactory import DataBusFactory
            from nle_library.device.GenericConnector import GenericConnector
            conn = GenericConnector(DataBusFactory.newSocketDataBus("192.168.1.200", 8899))
            conn.sendRtuWriteData(1, channel, is_open, lambda d: None)
            print("[控制] 通道%d -> %s" % (channel, "开" if is_open else "关"))
        except Exception as e:
            print("[控制] 调用失败（需 py36 + nle_library）：%s" % e)

    # ---------- 后台刷新 ----------
    def _camera_loop(self):
        while self._running:
            try:
                r = requests.get(CAMERA_SNAPSHOT, timeout=2)
                img = QImage.fromData(r.content)
                self.cameraLabel.setPixmap(QPixmap.fromImage(img).scaled(
                    self.cameraLabel.width(), self.cameraLabel.height(), QtCore.Qt.KeepAspectRatio))
            except Exception:
                pass
            time.sleep(0.5)

    def _data_loop(self):
        while self._running:
            if self.token:
                self.tempLabel.setText("温度：" + self.read_sensor(API_TAG_TEMP))
                self.humiLabel.setText("湿度：" + self.read_sensor(API_TAG_HUM))
            time.sleep(2)

    def closeEvent(self, event):
        self._running = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MonitorWindow()
    window.show()
    sys.exit(app.exec_())
