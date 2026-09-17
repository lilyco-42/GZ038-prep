# -*- coding: utf-8 -*-
"""
气象系统 (子任务2-6)

功能:
  将与 IoT 连接的 温度/湿度/光照/CO2/噪音 共 5 个传感器的实时数据,
  每 10 秒一次刷新到 LED 屏幕显示。
  显示格式: 温度 xx，湿度 xx，光照 xx，CO2 xx，噪音 xx

运行: python weather.py
依赖: 仅 Python 标准库(tkinter / urllib / json), 无需第三方包。
说明:
  - 默认从云服务(config.json)读取真实数据;
  - 若云服务不可达, 自动切换 demo 模拟数据, 保证界面可演示。
"""
import os
import sys
import threading
import time
import tkinter as tk

from nle_cloud import create_client, load_config

APP_NAME = "气象系统"
REFRESH_SEC = 10

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CFG = {
    "mode": "cloud",
    "base_url": "http://192.168.0.138",
    "username": "",
    "password": "",
    "refresh_sec": REFRESH_SEC,
    "sensors": {
        "温度": "m_temp",
        "湿度": "m_hum",
        "光照": "m_light",
        "CO2": "m_co2",
        "噪音": "m_noise",
    },
}


class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config(CONFIG_PATH, DEFAULT_CFG)
        self.refresh_sec = int(self.cfg.get("refresh_sec", REFRESH_SEC))
        self.sensor_names = list(self.cfg["sensors"].keys())
        self.sensor_tags = [self.cfg["sensors"][n] for n in self.sensor_names]

        self.client = create_client(self.cfg.get("mode", "cloud"),
                                    self.cfg.get("base_url", ""),
                                    self.cfg.get("username", ""),
                                    self.cfg.get("password", ""))
        self.running = True

        self._build_ui()
        # 后台线程周期性刷新
        threading.Thread(target=self._loop, daemon=True).start()

    # ------------------------------------------------------------------ #
    # LED 大屏风格界面
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.root.title(APP_NAME)
        self.root.configure(bg="#000000")
        self.root.geometry("900x360")

        tk.Label(self.root, text="气 象 监 测", font=("Microsoft YaHei", 28, "bold"),
                 bg="#000000", fg="#FFD700").pack(pady=(18, 6))

        # LED 屏主体: 黑底, 绿色数码字
        self.led = tk.Label(self.root,
                            text="温度 --，湿度 --，光照 --，CO2 --，噪音 --",
                            font=("Consolas", 26, "bold"),
                            bg="#000000", fg="#00FF66", justify="center")
        self.led.pack(expand=True, fill="both", padx=20)

        self.status = tk.Label(self.root, text="正在连接...",
                               font=("Microsoft YaHei", 11),
                               bg="#000000", fg="#888888")
        self.status.pack(pady=(0, 10))

    # ------------------------------------------------------------------ #
    # 后台采集 + 定时刷新
    # ------------------------------------------------------------------ #
    def _loop(self):
        # 先尝试登录(真实模式); 失败则用模拟
        try:
            if not self.client.login():
                raise RuntimeError("login failed")
            self.client.bind_first_device()
            mode_txt = "实时数据"
        except Exception:
            self.client = create_client("demo", "", "", "")
            self.client.login()
            mode_txt = "演示数据(云服务不可达)"

        while self.running:
            try:
                data = self.client.read_sensors(self.sensor_tags)
                line = self._format_line(data)
                self.root.after(0, lambda l=line: self.led.config(text=l))
                self.root.after(0, lambda m=mode_txt: self.status.config(
                    text="%s  |  每 %d 秒刷新  |  %s" % (
                        time.strftime("%H:%M:%S"), self.refresh_sec, m)))
            except Exception:
                pass
            # 分段睡眠, 便于快速退出
            for _ in range(self.refresh_sec * 10):
                if not self.running:
                    return
                time.sleep(0.1)

    def _format_line(self, data):
        parts = []
        for name, tag in zip(self.sensor_names, self.sensor_tags):
            v = data.get(tag)
            parts.append("%s %s" % (name, "--" if v is None else ("%.0f" % v)))
        # 赛题格式: 温度 xx，湿度 xx，光照 xx，CO2 xx，噪音 xx
        return "，".join(parts)

    def stop(self):
        self.running = False


def main():
    root = tk.Tk()
    app = WeatherApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
