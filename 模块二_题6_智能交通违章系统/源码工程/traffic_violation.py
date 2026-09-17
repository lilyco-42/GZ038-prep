# -*- coding: utf-8 -*-
"""
智能交通违章系统 (子任务2-6)

功能:
  1. 点击"开始监控"后, 三色灯每隔 light_seconds 秒轮流切换(绿->黄->红->绿),
     界面上的红绿灯动画同步播放; 绿灯状态下不显示汽车。
  2. 三张电子标签绑定车牌 A81237 / A21456 / A36888。
  3. 红灯时, 中距离一体机感应到电子标签:
       - 显示汽车;
       - 若该标签对应的车牌在系统登记表里 -> 提示"车辆闯红灯"并显示车牌;
       - 否则显示车牌"未登记"。
  4. 切到非红灯后, 界面恢复初始(隐藏汽车、清空提示)。
  5. 所有设备数据从串口服务器 TCP 模式获取 (见 tcp_bus.py)。

运行: python traffic_violation.py
"""
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import tcp_bus

APP_NAME = "智能交通违章系统"
DEFAULT_CONFIG = {
    "serial_server_ip": "172.18.0.15",
    "serial_server_port": 4196,
    "mode": "demo",
    "light_seconds": 10,
    "registered_plates": ["A81237", "A21456", "A36888"],
    "tag_to_plate": {
        "E28011600000000000000101": "A81237",
        "E28011600000000000000102": "A21456",
        "E28011600000000000000103": "A36888",
    },
}

# 灯色顺序: 绿 -> 黄 -> 红 -> 绿
LIGHT_ORDER = ["green", "yellow", "red"]


class TrafficApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x560")
        self.root.configure(bg="#F5F5F5")

        self.cfg = tcp_bus.load_config(DEFAULT_CONFIG)
        self.bus = tcp_bus.TcpBus(self.cfg)

        self.running = False
        self.light_index = 0          # 当前灯色下标
        self.cycle_tick = 0
        self.violation_shown = False  # 本次红灯周期是否已弹出违章提示

        self._build_ui()
        self._draw_light("green")
        self._hide_car()

    # ---------------- 界面 ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="智能交通违章监控系统",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#B71C1C", fg="white", pady=8).pack(fill="x")

        top = tk.Frame(self.root)
        top.pack(fill="x", pady=8)
        self.btn_start = tk.Button(top, text="开始监控", bg="#4CAF50", fg="white",
                                   font=("Microsoft YaHei", 12, "bold"),
                                   relief=tk.FLAT, command=self.start_monitor)
        self.btn_start.pack(side="left", padx=20, fill="x", expand=True)
        self.btn_stop = tk.Button(top, text="停止监控", bg="#F44336", fg="white",
                                  font=("Microsoft YaHei", 12, "bold"),
                                  relief=tk.FLAT, command=self.stop_monitor,
                                  state=tk.DISABLED)
        self.btn_stop.pack(side="left", padx=20, fill="x", expand=True)

        body = tk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=10)

        # 左: 红绿灯动画
        left = tk.LabelFrame(body, text="红绿灯", font=("Microsoft YaHei", 11))
        left.pack(side="left", padx=6)
        self.cv_light = tk.Canvas(left, width=120, height=300, bg="#222")
        self.cv_light.pack(padx=10, pady=10)
        self.light_circles = {}

        # 右: 道路/汽车区域 + 提示
        right = tk.LabelFrame(body, text="路口", font=("Microsoft YaHei", 11))
        right.pack(side="left", fill="both", expand=True, padx=6)
        self.cv_road = tk.Canvas(right, width=440, height=300, bg="#37474F")
        self.cv_road.pack(padx=10, pady=10)
        self._road_items = []

        self.var_msg = tk.StringVar(value="状态: 未开始监控")
        tk.Label(self.root, textvariable=self.var_msg,
                 font=("Microsoft YaHei", 11), fg="#333").pack(pady=6)

    def _draw_light(self, active):
        """绘制三色灯, active in green/yellow/red。"""
        self.cv_light.delete("all")
        positions = {"red": 50, "yellow": 150, "green": 250}
        colors = {"red": ("#550000", "#FF1744"),
                  "yellow": ("#555500", "#FFEB3B"),
                  "green": ("#005500", "#00E676")}
        self.light_circles = {}
        for name, y in positions.items():
            off, on = colors[name]
            fill = on if name == active else off
            c = self.cv_light.create_oval(30, y - 35, 90, y + 35, fill=fill,
                                          outline="#000", width=2)
            self.light_circles[name] = c

    def _draw_car(self):
        """在道路上画一辆小汽车(违章抓拍示意)。"""
        self.cv_road.delete("all")
        # 路面
        self.cv_road.create_rectangle(0, 250, 440, 300, fill="#263238")
        for x in range(0, 440, 50):
            self.cv_road.create_line(x, 275, x + 25, 275, fill="#FFEB3B", width=3)
        # 车身
        self.cv_road.create_rectangle(150, 180, 290, 240, fill="#FF7043", outline="#BF360C", width=2)
        self.cv_road.create_rectangle(185, 150, 255, 185, fill="#FFAB91", outline="#BF360C")
        # 车轮
        self.cv_road.create_oval(165, 235, 195, 265, fill="#212121")
        self.cv_road.create_oval(245, 235, 275, 265, fill="#212121")
        # 车牌
        self.cv_road.create_rectangle(190, 205, 250, 225, fill="white", outline="black")

    def _hide_car(self):
        self.cv_road.delete("all")
        self.cv_road.create_rectangle(0, 250, 440, 300, fill="#263238")
        self.cv_road.create_text(220, 130, text="(无车辆)", fill="#90A4AE",
                                 font=("Microsoft YaHei", 16))

    def _set_plate_on_car(self, plate_text):
        # 在车牌位置写文字
        self.cv_road.delete("plate_txt")
        self.cv_road.create_text(220, 215, text=plate_text, fill="black",
                                 font=("Arial", 10, "bold"), tags="plate_txt")

    # ---------------- 监控控制 ---------------- #
    def start_monitor(self):
        if self.running:
            return
        self.running = True
        self.violation_shown = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.var_msg.set("状态: 监控中...")
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop_monitor(self):
        self.running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.var_msg.set("状态: 已停止")
        self.bus.set_light(False, False, False)   # 停止时三色灯全灭

    # ---------------- 后台循环 ---------------- #
    def _monitor_loop(self):
        interval = 1.0
        step = 0
        while self.running:
            # 每 light_seconds 秒切一次灯
            if step % int(self.cfg["light_seconds"]) == 0:
                self.light_index = (self.light_index + 1) % len(LIGHT_ORDER)
                color = LIGHT_ORDER[self.light_index]
                self.root.after(0, lambda c=color: self._on_light_changed(c))
            step += 1

            color = LIGHT_ORDER[self.light_index]
            if color == "red":
                epc = self.bus.read_epc()
                if epc:
                    self.root.after(0, lambda e=epc: self._on_tag_on_red(e))
            else:
                # 非红灯: 恢复初始
                if self.violation_shown:
                    self.violation_shown = False
                    self.root.after(0, self._reset_scene)

            time.sleep(interval)

    def _on_light_changed(self, color):
        self._draw_light(color)
        if color == "green":
            self.bus.set_light(False, False, True)
            self.var_msg.set("状态: 绿灯, 通行")
        elif color == "yellow":
            self.bus.set_light(False, True, False)
            self.var_msg.set("状态: 黄灯")
        else:
            self.bus.set_light(True, False, False)
            self.var_msg.set("状态: 红灯, 禁止通行")

    def _on_tag_on_red(self, epc):
        """红灯时读到标签: 显示汽车并判车牌。"""
        if self.violation_shown:
            return
        self.violation_shown = True

        tag = (epc or "").strip().upper()
        plate = self.cfg.get("tag_to_plate", {}).get(tag)
        registered = plate in self.cfg.get("registered_plates", [])

        self._draw_car()
        if registered:
            self._set_plate_on_car(plate)
            self.var_msg.set("状态: 车辆闯红灯! 车牌: %s" % plate)
        else:
            self._set_plate_on_car("未登记")
            self.var_msg.set("状态: 车辆闯红灯! 车牌: 未登记")

    def _reset_scene(self):
        self._hide_car()
        self.var_msg.set("状态: 监控中...")


def main():
    root = tk.Tk()
    try:
        TrafficApp(root)
    except Exception as exc:
        messagebox.showerror(APP_NAME, "启动失败: %s" % exc)
        return
    root.mainloop()


if __name__ == "__main__":
    main()
