# -*- coding: utf-8 -*-
"""
子任务2-6 行人闯红灯监控系统（GZ038 第8套）
====================================================================
通过云服务系统采集传感器值、控制执行器状态:
  - 微动开关代表红绿灯: 默认(断开)为绿灯, 闭合为红灯。
  - 红灯状态: 三色灯仅红灯亮, 其他灯灭。
  - 绿灯状态: 三色灯仅绿灯亮, 其他灯灭。
  - 绿灯状态: 显示"绿灯放行"图, 此时红外对射即使报警也不变。
  - 红灯状态且红外对射不报警: 显示"红灯禁行"图, 报警灯灭。
  - 红灯状态且红外对射报警: 显示"行人闯红灯"图, 报警灯报警。

  - TCP 模式连接串口服务器 COM3 口, 通过 COM3 控制 "C-1" ZigBee 黑色开发板
    D4(红灯)、D3(绿灯)、D6(报警灯), 与三色灯开关状态同步。

运行: python pedestrian_monitor.py
配置: 同目录 config.json; 云客户端 nle_cloud.py
"""
import json
import os
import sys
import socket
import threading
import time
import tkinter as tk
from datetime import datetime

APP_NAME = "行人闯红灯监控系统"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


# ------------------------------------------------------------------ #
# 配置
# ------------------------------------------------------------------ #
def load_config():
    default = {
        "mode": "demo",
        "cloud": {"base_url": "http://192.168.0.138",
                  "username": "18912345600", "password": "123456"},
        "device": {
            "device_id": 0,
            "switch_tag": "m_travelSwitch_singleWheel",  # 微动开关(红绿灯)
            "laser_tag": "m_laser",                       # 红外对射
            "red_lamp_tag": "m_multi_red",                # 三色灯-红
            "green_lamp_tag": "m_multi_green",           # 三色灯-绿
            "alarm_tag": "m_rotating_lamp",               # 报警灯(转动指示灯)
        },
        "serial_server": {
            "host": "192.168.0.15", "port": 4103, "channel": "COM3",
            "d4_red": "D4", "d3_green": "D3", "d6_alarm": "D6",
        },
        "poll_interval_sec": 1,
    }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return default


# ------------------------------------------------------------------ #
# TCP 串口服务器客户端: 经 COM3 控制 C-1 ZigBee 板 D4/D3/D6
# ------------------------------------------------------------------ #
class TcpSerialLamp(object):
    """TCP 连接串口服务器(COM3), 下发灯控指令。

    串口服务器把 COM3 映射到 TCP 端口; C-1 ZigBee 板固件约定接收文本指令:
        "D4,1\\n"  D4 亮(红灯)   "D4,0\\n"  D4 灭
        "D3,1\\n"  D3 亮(绿灯)   "D3,0\\n"  D3 灭
        "D6,1\\n"  D6 亮(报警)   "D6,0\\n"  D6 灭
    实际协议以现场 C-1 固件为准, 在这里改 send 即可。
    """

    def __init__(self, ss_cfg):
        self.host = ss_cfg.get("host", "")
        self.port = int(ss_cfg.get("port", 4103))
        self.d4 = ss_cfg.get("d4_red", "D4")
        self.d3 = ss_cfg.get("d3_green", "D3")
        self.d6 = ss_cfg.get("d6_alarm", "D6")
        self.sock = None
        self.lock = threading.Lock()

    def connect(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=3)
            return True
        except Exception:
            self.sock = None
            return False

    def _send(self, pin, on):
        if self.sock is None:
            if not self.connect():
                return
        try:
            cmd = "%s,%d\n" % (pin, 1 if on else 0)
            with self.lock:
                self.sock.sendall(cmd.encode("ascii"))
        except Exception:
            # 断线重连一次
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def set_red(self, on):
        self._send(self.d4, on)

    def set_green(self, on):
        self._send(self.d3, on)

    def set_alarm(self, on):
        self._send(self.d6, on)


# ------------------------------------------------------------------ #
# 云服务读取(带 demo 模拟)
# ------------------------------------------------------------------ #
class CloudReader(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = None
        self.device_id = cfg["device"].get("device_id")
        self._demo_tick = 0
        if cfg.get("mode") != "demo":
            try:
                from nle_cloud import NLECloudClient
                c = cfg["cloud"]
                self.client = NLECloudClient(c["base_url"], c["username"], c["password"])
                ok, _ = self.client.login()
                if ok:
                    self.client.bindFirstDevice() if hasattr(self.client, "bindFirstDevice") else None
            except Exception:
                self.client = None

    def read(self, tag):
        """返回传感器 0/1, 读不到返回 None。"""
        if self.client is not None:
            try:
                v = self.client.fetch_sensor([tag], [self.device_id]) if hasattr(
                    self.client, "fetch_sensor") else None
                if v and tag in v and v[tag].get("value") is not None:
                    return 1 if float(v[tag]["value"]) >= 1.0 else 0
            except Exception:
                pass
            return None
        # demo 模拟: 微动开关默认 0(绿灯), 每若干秒切一次红灯; 红外对射偶尔报警
        self._demo_tick += 1
        if tag == self.cfg["device"]["switch_tag"]:
            return 1 if (self._demo_tick // 8) % 2 == 1 else 0
        if tag == self.cfg["device"]["laser_tag"]:
            return 1 if (self._demo_tick % 10 == 0) else 0
        return None


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class PedestrianApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.reader = CloudReader(self.cfg)
        self.lamp = TcpSerialLamp(self.cfg["serial_server"])
        self.running = True

        # 记录上一次下发状态, 避免重复
        self.last_red = -1
        self.last_green = -1
        self.last_alarm = -1

        self.root.title(APP_NAME)
        self.root.geometry("760x620")
        self.root.configure(bg="#F4F6F8")

        self._build_ui()
        self._poll_loop()

    # ---------------- UI ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="行人闯红灯监控系统",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#1565C0", fg="white", pady=10).pack(fill="x")

        # 场景图区域: 用大色块+文字模拟三幅图
        self.cv = tk.Canvas(self.root, width=720, height=360, bg="white",
                           relief="ridge", bd=2)
        self.cv.pack(pady=10)

        # 三色灯指示
        lamps = tk.Frame(self.root, bg="#F4F6F8")
        lamps.pack(pady=4)
        self.lbl_red = tk.Label(lamps, text="红灯", font=("Microsoft YaHei", 12, "bold"),
                                width=8, bg="#424242", fg="white")
        self.lbl_red.pack(side="left", padx=10)
        self.lbl_green = tk.Label(lamps, text="绿灯", font=("Microsoft YaHei", 12, "bold"),
                                  width=8, bg="#424242", fg="white")
        self.lbl_green.pack(side="left", padx=10)
        self.lbl_alarm = tk.Label(lamps, text="报警灯", font=("Microsoft YaHei", 12, "bold"),
                                   width=8, bg="#424242", fg="white")
        self.lbl_alarm.pack(side="left", padx=10)

        self.lbl_status = tk.Label(self.root, text="状态: 监听中...",
                                   font=("Microsoft YaHei", 11), fg="#555")
        self.lbl_status.pack(pady=6)

    # ---------------- 轮询 ---------------- #
    def _poll_loop(self):
        if not self.running:
            return
        try:
            self.step()
        except Exception as exc:
            self.lbl_status.config(text="状态: %s" % exc)
        self.root.after(int(self.cfg["poll_interval_sec"]) * 1000, self._poll_loop)

    def step(self):
        d = self.cfg["device"]
        # 微动开关: 默认(0/断开)=绿灯, 闭合(1)=红灯
        sw = self.reader.read(d["switch_tag"])
        # 红外对射: 1=报警
        laser = self.reader.read(d["laser_tag"])

        red_lit = 0
        green_lit = 0
        alarm_lit = 0
        scene_text = "--"
        scene_color = "#9E9E9E"

        if sw is None:
            self.lbl_status.config(text="状态: 等待云服务数据...")
            return

        if sw == 0:
            """绿灯放行: 仅绿灯亮, 红外报警也不变。"""
            green_lit = 1
            red_lit = 0
            alarm_lit = 0
            scene_text = "绿灯放行"
            scene_color = "#2E7D32"
        else:
            """红灯: 仅红灯亮。"""
            red_lit = 1
            green_lit = 0
            if laser == 1:
                """红灯 + 红外报警 -> 行人闯红灯, 报警灯亮。"""
                alarm_lit = 1
                scene_text = "行人闯红灯"
                scene_color = "#C62828"
            else:
                """红灯 + 无红外报警 -> 红灯禁行, 报警灯灭。"""
                alarm_lit = 0
                scene_text = "红灯禁行"
                scene_color = "#EF6C00"

        # 下发三色灯(云服务)
        self._push(d["red_lamp_tag"], red_lit, "red")
        self._push(d["green_lamp_tag"], green_lit, "green")
        self._push(d["alarm_tag"], alarm_lit, "alarm")

        # 同步串口服务器 COM3 -> C-1 板 D4/D3/D6
        self.lamp.set_red(red_lit)
        self.lamp.set_green(green_lit)
        self.lamp.set_alarm(alarm_lit)

        # 刷新界面
        self._draw_scene(scene_text, scene_color, red_lit, green_lit, alarm_lit)
        self.lbl_status.config(
            text="状态: %s | 微动开关=%s 红外=%s" % (scene_text, sw, laser))

    def _push(self, tag, value, kind):
        last = {"red": self.last_red, "green": self.last_green,
                "alarm": self.last_alarm}[kind]
        if value == last:
            return
        if self.reader.client is not None:
            try:
                self.reader.client.send_command(self.reader.device_id, tag, value)
            except Exception:
                pass
        if kind == "red":
            self.last_red = value
        elif kind == "green":
            self.last_green = value
        else:
            self.last_alarm = value

    def _draw_scene(self, text, color, red, green, alarm):
        self.cv.delete("all")
        self.cv.create_rectangle(0, 0, 720, 360, fill=color, outline="")
        self.cv.create_text(360, 180, text=text, fill="white",
                            font=("Microsoft YaHei", 40, "bold"))
        self.lbl_red.config(bg="#E53935" if red else "#424242")
        self.lbl_green.config(bg="#43A047" if green else "#424242")
        self.lbl_alarm.config(bg="#FB8C00" if alarm else "#424242")

    def on_close(self):
        self.running = False
        # 退出前三色灯、报警灯全灭
        d = self.cfg["device"]
        if self.reader.client is not None:
            try:
                self.reader.client.send_command(self.reader.device_id, d["red_lamp_tag"], 0)
                self.reader.client.send_command(self.reader.device_id, d["green_lamp_tag"], 0)
                self.reader.client.send_command(self.reader.device_id, d["alarm_tag"], 0)
            except Exception:
                pass
        self.lamp.set_red(0)
        self.lamp.set_green(0)
        self.lamp.set_alarm(0)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PedestrianApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
