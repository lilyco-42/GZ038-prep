# -*- coding: utf-8 -*-
"""
车库管理系统（2-6 智能停车场 / GZ038 第3套）

功能:
  1. 车位总数固定 10 个。
  2. 红外对射感应到车辆入库时，已用车位 +1；
     LED 屏显示 "已用:X  剩余数量:x"，界面空位同步刷新。
  3. 已用车位达到总数(超过设定值)时，提示"车位已满"，LED 屏显示"车位已满"。
  4. 红外对射感应到时，播放小车入库动画。
  5. 程序通过 TCP 模式访问串口服务器读取红外对射数据并控制设备。

运行: python garage.py
依赖: Python 3.x, 标准库 tkinter；联网读串口服务器用 socket（无外网新包）。
"""
import json
import os
import random
import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox

APP_NAME = "车库管理系统"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "serial_server": {"ip": "172.18.0.15", "port": 8001},
    "total_spots": 10,
    "poll_interval_ms": 300,
    "simulate": True,
}


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception:
            pass
    return cfg


# ------------------------------------------------------------------ #
# 红外对射读数：TCP 串口服务器
# ------------------------------------------------------------------ #
class BeamSensor:
    """通过 TCP 访问串口服务器读取红外对射状态。

    真实设备：连上串口服务器后，按 Modbus/ASCII 读红外对射开关量，
    感应到车辆时返回 True。这里抽象为 read_beam()，
    串口不可达时降级为模拟模式（按按钮/定时模拟一次入场）。
    """

    def __init__(self, cfg):
        self.ip = cfg["serial_server"]["ip"]
        self.port = int(cfg["serial_server"]["port"])
        self.simulate = bool(cfg.get("simulate", True))
        self.sock = None
        self.connected = False

    def connect(self):
        if self.simulate:
            return True
        try:
            self.sock = socket.create_connection((self.ip, self.port), timeout=1.5)
            self.connected = True
        except Exception:
            self.connected = False
        return self.connected

    def read_beam(self):
        """返回 True 表示本次检测到一次车辆入场（红外对射触发）。"""
        if self.simulate:
            return False  # 模拟模式由界面按钮/演示触发
        try:
            # TODO(现场): 组帧读红外对射开关量，边沿触发即返回 True
            return False
        except Exception:
            return False


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class GarageApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.total = int(self.cfg.get("total_spots", 10))
        self.used = 0
        self.full = False

        self.sensor = BeamSensor(self.cfg)
        self.sensor.connect()

        self.running = True
        self._anim = None  # 动画 after id

        self._build_ui()
        self._refresh()
        self._poll_loop()

    # ---------------- 界面 ---------------- #
    def _build_ui(self):
        self.root.title(APP_NAME)
        self.root.geometry("860x560")
        self.root.configure(bg="#1E2A38")

        tk.Label(self.root, text="智能停车场 · 车库管理系统",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#1E2A38", fg="#FFC107", pady=8).pack(fill="x")

        # 顶部统计
        top = tk.Frame(self.root, bg="#1E2A38")
        top.pack(fill="x", padx=12)
        self.lb_used = tk.Label(top, text="", font=("Microsoft YaHei", 20, "bold"),
                                bg="#1E2A38", fg="#4CAF50")
        self.lb_used.pack(side="left", padx=20)
        self.lb_free = tk.Label(top, text="", font=("Microsoft YaHei", 20, "bold"),
                                bg="#1E2A38", fg="#2196F3")
        self.lb_free.pack(side="right", padx=20)

        # 车位画布
        self.canvas = tk.Canvas(self.root, bg="#0F1822", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=8)

        # LED 屏（模拟大屏显示）
        self.led = tk.Label(self.root, text="LED: 已用:0  剩余:10",
                            font=("Consolas", 16, "bold"),
                            bg="black", fg="red", anchor="w", padx=10)
        self.led.pack(fill="x", padx=12)

        # 底部按钮
        bottom = tk.Frame(self.root, bg="#1E2A38")
        bottom.pack(fill="x", padx=12, pady=8)
        self.btn_in = tk.Button(bottom, text="车辆入场(模拟红外对射)",
                                font=("Microsoft YaHei", 12, "bold"),
                                bg="#4CAF50", fg="white", relief=tk.FLAT,
                                command=self.car_in)
        self.btn_in.pack(side="left", fill="x", expand=True, padx=4)
        self.btn_reset = tk.Button(bottom, text="复位",
                                   font=("Microsoft YaHei", 12),
                                   bg="#607D8B", fg="white", relief=tk.FLAT,
                                   command=self.reset)
        self.btn_reset.pack(side="left", fill="x", expand=True, padx=4)

    # ---------------- 车位绘制 ---------------- #
    def _draw_spots(self):
        self.canvas.delete("spot")
        cols, cw, ch = 5, 120, 70
        ox, oy = 30, 30
        for i in range(self.total):
            r, c = divmod(i, cols)
            x0 = ox + c * (cw + 15)
            y0 = oy + r * (ch + 20)
            used = i < self.used
            color = "#C62828" if used else "#2E7D32"
            self.canvas.create_rectangle(x0, y0, x0 + cw, y0 + ch,
                                         fill=color, outline="#FFFFFF", width=2,
                                         tags="spot")
            self.canvas.create_text(x0 + cw / 2, y0 + ch / 2,
                                    text="%02d" % (i + 1),
                                    fill="white", font=("Arial", 16, "bold"),
                                    tags="spot")

    def _refresh(self):
        free = max(0, self.total - self.used)
        self.lb_used.config(text="已用车位: %d" % self.used)
        self.lb_free.config(text="剩余车位: %d" % free)
        # LED 屏
        if self.full:
            self.led.config(text="LED: 车位已满，请等候")
        else:
            self.led.config(text="LED: 已用:%d  剩余数量:%d" % (self.used, free))
        self._draw_spots()

    # ---------------- 车辆入场 ---------------- #
    def car_in(self):
        if self.full:
            messagebox.showwarning(APP_NAME, "车位已满，禁止入场！")
            return
        self.used += 1
        if self.used >= self.total:
            self.full = True
        self._refresh()
        self._play_car_animation()

    def reset(self):
        self.used = 0
        self.full = False
        self._refresh()

    # ---------------- 小车入库动画 ---------------- #
    def _play_car_animation(self):
        """在画布底部画一辆小车从右开到已用车位的位置。"""
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 400
        car = self.canvas.create_rectangle(w - 60, h - 60, w - 10, h - 30,
                                           fill="#FFC107", outline="", tags="car")
        steps = 30
        dx = (w - 200) / steps

        def step(n):
            if n > 0:
                self.canvas.move(car, -dx, 0)
                self._anim = self.root.after(20, lambda: step(n - 1))
            else:
                self.canvas.delete(car)

        step(steps)

    # ---------------- 红外对射轮询 ---------------- #
    def _poll_loop(self):
        if not self.running:
            return
        try:
            if self.sensor.read_beam():
                self.root.after(0, self.car_in)
        except Exception:
            pass
        self.root.after(int(self.cfg.get("poll_interval_ms", 300)), self._poll_loop)

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = GarageApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
