# -*- coding: utf-8 -*-
"""
大厅环境系统 (子任务2-7)

功能:
  1. 手动/自动模式切换:
     - 手动模式: 不执行自动逻辑, 界面上电灯/风扇/报警灯按钮可用;
     - 自动模式: 执行自动逻辑, 界面按钮禁用。
  2. 程序运行时门为关(电动推杆向外伸长到最长)。
  3. 实时采集并显示 ZigBee 温度、ZigBee 湿度、烟雾(有线)、人体(有线)。
  4. 手动模式: 点击界面按钮控制对应设备。
  5. 自动模式:
     - 监测到烟雾 -> 自动打开报警灯;
     - 温度超过设定阈值(界面可改) -> 自动开风扇, 否则关;
     - 人体感应到有人 -> 自动开电灯且自动开门, 否则关电灯且关门。
  6. 电灯/风扇/报警灯均带动画。
  7. 设备数据从串口服务器 TCP 模式获取。

运行: python hall_env.py
"""
import json
import math
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

APP_NAME = "大厅环境系统"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "serial_server_ip": "172.18.0.15",
    "serial_server_port": 4196,
    "mode": "demo",
    "temp_threshold": 30.0,
    "sensor_tags": {
        "zigbee_temp": "z_temp",
        "zigbee_hum": "z_hum",
        "smoke": "m_smoke",
        "body": "m_microwave",
    },
    "actuator_tags": {
        "lamp": "m_lamp",
        "fan": "m_fan",
        "alarm": "m_rotating_lamp",
        "pushrod_putt": "m_pushrod_putt",
        "pushrod_back": "m_pushrod_back",
    },
}


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


# ------------------------------------------------------------------ #
# 串口服务器 TCP 总线
# ------------------------------------------------------------------ #
class TcpBus(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.mode = cfg.get("mode", "demo")
        self.connector = None
        self._init_real()

    def _init_real(self):
        if self.mode != "cloud":
            return
        try:
            from nle_library.databus import DataBusFactory
            from nle_library.device import GenericConnector
            bus = DataBusFactory.newSocketDataBus(
                self.cfg["serial_server_ip"], int(self.cfg["serial_server_port"]))
            self.connector = GenericConnector(bus)
        except Exception as exc:
            print("TCP 总线连接失败, 回退 demo: %s" % exc)
            self.mode = "demo"
            self.connector = None

    def read_sensor(self, apitag):
        """读网关某传感器最新值, 返回 float; demo 下给模拟值。"""
        if self.connector is not None:
            box = [None]

            def cb(data):
                try:
                    box[0] = float(getattr(data, "value", data))
                except Exception:
                    box[0] = None

            try:
                self.connector.sendGatewaySearch(apitag, cb)
                time.sleep(0.15)
            except Exception:
                pass
            return box[0]
        return self._sim(apitag)

    def _sim(self, apitag):
        """demo 模拟: 温度缓慢变化, 烟雾/人体偶发。"""
        now = time.time()
        if apitag == self.cfg["sensor_tags"]["zigbee_temp"]:
            return round(26 + 6 * math.sin(now / 20.0), 1)
        if apitag == self.cfg["sensor_tags"]["zigbee_hum"]:
            return round(55 + 5 * math.sin(now / 30.0), 1)
        if apitag == self.cfg["sensor_tags"]["smoke"]:
            return 1 if int(now) % 25 < 3 else 0          # 偶发烟雾
        if apitag == self.cfg["sensor_tags"]["body"]:
            return 1 if int(now) % 12 < 6 else 0          # 偶有人体
        return None

    def control(self, apitag, value):
        if self.connector is None:
            return
        try:
            self.connector.sendGatewayControl(apitag, 1, 1 if value else 0,
                                               lambda d: None)
        except Exception as exc:
            print("下发 %s 失败: %s" % (apitag, exc))


# ------------------------------------------------------------------ #
# 风扇动画
# ------------------------------------------------------------------ #
class FanCanvas(tk.Canvas):
    def __init__(self, master, size=120):
        super().__init__(master, width=size, height=size, bg="white",
                         highlightthickness=1, highlightbackground="#CCC")
        self.size = size
        self._angle = 0
        self._running = False
        self._job = None
        self._draw()

    def _draw(self):
        self.delete("all")
        c = self.size // 2
        r = self.size * 0.36
        for i in range(4):
            a = self._angle + i * 90
            x1 = c + r * math.cos(math.radians(a))
            y1 = c + r * math.sin(math.radians(a))
            self.create_line(c, c, x1, y1, width=8, fill="#1976D2", capstyle=tk.ROUND)
        self.create_oval(c - 12, c - 12, c + 12, c + 12, fill="#FF9800")

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self):
        self._running = False
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self._angle = 0
        self._draw()

    def _tick(self):
        if not self._running:
            return
        self._angle = (self._angle + 12) % 360
        self._draw()
        self._job = self.after(50, self._tick)


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class HallApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("720x600")
        self.root.configure(bg="#F5F5F5")

        self.cfg = load_cfg()
        self.bus = TcpBus(self.cfg)
        self.st = self.cfg["sensor_tags"]
        self.ac = self.cfg["actuator_tags"]

        self.mode = "manual"          # manual / auto
        self.temp_threshold = float(self.cfg.get("temp_threshold", 30.0))

        # 设备当前状态(软件侧)
        self.lamp_on = False
        self.fan_on = False
        self.alarm_on = False
        self.door_open = False         # False=关(推杆伸长最长)

        self.running = True
        self._build_ui()

        # 启动: 门为关(推杆伸长到最长)
        self._set_door(False, push=True)

        self.root.after(500, self._poll_loop)

    # ---------------- 界面 ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="大厅环境监控系统",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#00695C", fg="white", pady=8).pack(fill="x")

        # 模式切换
        mode_bar = tk.Frame(self.root)
        mode_bar.pack(fill="x", padx=10, pady=6)
        self.var_mode = tk.StringVar(value="manual")
        tk.Radiobutton(mode_bar, text="手动模式", variable=self.var_mode,
                       value="manual", command=self._on_mode_change).pack(side="left", padx=20)
        tk.Radiobutton(mode_bar, text="自动模式", variable=self.var_mode,
                       value="auto", command=self._on_mode_change).pack(side="left", padx=20)
        tk.Label(mode_bar, text="温度阈值:").pack(side="left", padx=(20, 2))
        self.var_th = tk.StringVar(value=str(self.temp_threshold))
        tk.Entry(mode_bar, textvariable=self.var_th, width=6).pack(side="left")
        tk.Button(mode_bar, text="设置", command=self._set_threshold).pack(side="left", padx=4)

        # 数据区
        data = tk.Frame(self.root, bd=1, relief="groove")
        data.pack(fill="x", padx=10, pady=6)
        self.var_temp = tk.StringVar(value="--")
        self.var_hum = tk.StringVar(value="--")
        self.var_smoke = tk.StringVar(value="正常")
        self.var_body = tk.StringVar(value="无人")
        self._data_cell(data, "ZigBee温度", self.var_temp, "℃", 0)
        self._data_cell(data, "ZigBee湿度", self.var_hum, "%", 1)
        self._data_cell(data, "烟雾", self.var_smoke, "", 2)
        self._data_cell(data, "人体", self.var_body, "", 3)

        # 设备动画区
        dev = tk.Frame(self.root)
        dev.pack(fill="x", padx=10, pady=6)

        f1 = tk.LabelFrame(dev, text="电灯")
        f1.pack(side="left", expand=True, fill="x", padx=4)
        self.lb_lamp = tk.Label(f1, text="●", font=("Arial", 50), fg="#9E9E9E")
        self.lb_lamp.pack(pady=6)
        self.btn_lamp = tk.Button(f1, text="开灯", command=lambda: self._manual_lamp(True))
        self.btn_lamp.pack(side="left", padx=8)
        tk.Button(f1, text="关灯", command=lambda: self._manual_lamp(False)).pack(side="left", padx=8)

        f2 = tk.LabelFrame(dev, text="风扇")
        f2.pack(side="left", expand=True, fill="x", padx=4)
        self.fan = FanCanvas(f2, 110)
        self.fan.pack(pady=4)
        self.btn_fan = tk.Button(f2, text="开扇", command=lambda: self._manual_fan(True))
        self.btn_fan.pack(side="left", padx=8)
        tk.Button(f2, text="关扇", command=lambda: self._manual_fan(False)).pack(side="left", padx=8)

        f3 = tk.LabelFrame(dev, text="报警灯")
        f3.pack(side="left", expand=True, fill="x", padx=4)
        self.lb_alarm = tk.Label(f3, text="●", font=("Arial", 50), fg="#9E9E9E")
        self.lb_alarm.pack(pady=6)
        self.btn_alarm = tk.Button(f3, text="开报警", command=lambda: self._manual_alarm(True))
        self.btn_alarm.pack(side="left", padx=8)
        tk.Button(f3, text="关报警", command=lambda: self._manual_alarm(False)).pack(side="left", padx=8)

        # 门状态
        self.var_door = tk.StringVar(value="闸门: 关")
        tk.Label(self.root, textvariable=self.var_door,
                 font=("Microsoft YaHei", 12), fg="#00695C").pack(pady=6)

        self.var_status = tk.StringVar(value="状态: 手动模式")
        tk.Label(self.root, textvariable=self.var_status,
                 font=("Microsoft YaHei", 10), fg="#555").pack()

        self._refresh_button_state()

    def _data_cell(self, parent, name, var, unit, col):
        f = tk.Frame(parent)
        f.pack(side="left", expand=True, fill="x", padx=6, pady=6)
        tk.Label(f, text=name, font=("Microsoft YaHei", 11)).pack()
        tk.Label(f, textvariable=var, font=("Arial", 20, "bold"), fg="#00695C").pack()
        tk.Label(f, text=unit, font=("Microsoft YaHei", 9), fg="#888").pack()

    # ---------------- 模式 ---------------- #
    def _on_mode_change(self):
        self.mode = self.var_mode.get()
        self.var_status.set("状态: %s模式" % ("自动" if self.mode == "auto" else "手动"))
        self._refresh_button_state()

    def _refresh_button_state(self):
        # 自动模式禁用手动按钮; 手动模式启用
        state = tk.NORMAL if self.mode == "manual" else tk.DISABLED
        for b in (self.btn_lamp, self.btn_fan, self.btn_alarm):
            b.config(state=state)

    def _set_threshold(self):
        try:
            self.temp_threshold = float(self.var_th.get())
            self.cfg["temp_threshold"] = self.temp_threshold
        except ValueError:
            messagebox.showwarning(APP_NAME, "阈值需为数字")

    # ---------------- 手动控制 ---------------- #
    def _manual_lamp(self, on):
        self._set_lamp(on)

    def _manual_fan(self, on):
        self._set_fan(on)

    def _manual_alarm(self, on):
        self._set_alarm(on)

    # ---------------- 设备下发与界面 ---------------- #
    def _set_lamp(self, on):
        self.lamp_on = on
        self.bus.control(self.ac["lamp"], 1 if on else 0)
        self.lb_lamp.config(fg="#FFC107" if on else "#9E9E9E")

    def _set_fan(self, on):
        self.fan_on = on
        self.bus.control(self.ac["fan"], 1 if on else 0)
        if on:
            self.fan.start()
        else:
            self.fan.stop()

    def _set_alarm(self, on):
        self.alarm_on = on
        self.bus.control(self.ac["alarm"], 1 if on else 0)
        self.lb_alarm.config(fg="#F44336" if on else "#9E9E9E")

    def _set_door(self, open_, push=False):
        """门: open_=True 开门(推杆收回), False 关门(推杆伸长到最长)。"""
        self.door_open = open_
        # 先停两个方向
        self.bus.control(self.ac["pushrod_putt"], 0)
        self.bus.control(self.ac["pushrod_back"], 0)
        if open_:
            self.bus.control(self.ac["pushrod_back"], 1)   # 收回 = 开门
            self.var_door.set("闸门: 开")
        else:
            self.bus.control(self.ac["pushrod_putt"], 1)   # 伸长最长 = 关门
            self.var_door.set("闸门: 关")

    # ---------------- 采集与自动逻辑 ---------------- #
    def _poll_loop(self):
        if not self.running:
            return
        threading.Thread(target=self._collect, daemon=True).start()
        self.root.after(1500, self._poll_loop)

    def _collect(self):
        temp = self.bus.read_sensor(self.st["zigbee_temp"])
        hum = self.bus.read_sensor(self.st["zigbee_hum"])
        smoke = self.bus.read_sensor(self.st["smoke"])
        body = self.bus.read_sensor(self.st["body"])

        self.root.after(0, lambda: self._update_sensors(temp, hum, smoke, body))

        if self.mode == "auto":
            self._auto_logic(temp, smoke, body)

    def _update_sensors(self, temp, hum, smoke, body):
        self.var_temp.set("%.1f" % temp if temp is not None else "--")
        self.var_hum.set("%.1f" % hum if hum is not None else "--")
        self.var_smoke.set("报警!" if (smoke and smoke >= 1) else "正常")
        self.var_body.set("有人" if (body and body >= 1) else "无人")

    def _auto_logic(self, temp, smoke, body):
        # 1) 烟雾 -> 报警灯
        alarm = bool(smoke and smoke >= 1)
        if alarm != self.alarm_on:
            self._set_alarm(alarm)

        # 2) 温度超阈值 -> 风扇
        fan = (temp is not None and temp >= self.temp_threshold)
        if fan != self.fan_on:
            self._set_fan(fan)

        # 3) 人体 -> 电灯 + 门
        person = bool(body and body >= 1)
        if person != self.lamp_on:
            self._set_lamp(person)
        open_door = person
        if open_door != self.door_open:
            self._set_door(open_door)

    # ---------------- 退出 ---------------- #
    def on_close(self):
        self.running = False
        self._set_fan(False)
        self._set_lamp(False)
        self._set_alarm(False)
        self._set_door(False)   # 门关
        self.root.destroy()


def main():
    root = tk.Tk()
    app = HallApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
