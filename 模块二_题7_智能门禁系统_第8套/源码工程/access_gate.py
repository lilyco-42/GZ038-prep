# -*- coding: utf-8 -*-
"""
子任务2-7 智能门禁系统（GZ038 第8套）—— 入口端
====================================================================
业务规则:
  1. 入口端主界面默认关门（电动推杆伸出到底，行程开关辅助确认）。
  2. 检测 RFID 卡:
     - 注册卡: 开门（电动推杆缩回，接近开关辅助确认），界面显示绑定人员信息，
       此时人员状态为"离岗"。
     - 非注册卡: 不开门，LED 显示屏显示"未注册"，5 秒后无显示。
  3. 开门后:
     - 红外对射触发（表示人员已进门）: 直接关门，人员状态变更为"在岗"，
       LED 显示屏显示"请带好安全帽"。
     - 红外对射未触发: 10 秒后自动关门，界面人员信息清除，LED 显示屏无显示。

  电动推杆/行程开关/红外对射 -> 数字量采集器 -> 中心网关 -> 云服务系统。
  LED 显示屏 -> USB转RS232 -> 中心网关 -> 云服务系统。

运行: python access_gate.py
配置: 同目录 config.json; 注册卡 cards.json; 云客户端 nle_cloud.py
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime

APP_NAME = "智慧门禁入口端"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CARDS_FILE = os.path.join(BASE_DIR, "cards.json")

# 状态机
ST_CLOSED     = "CLOSED"       # 默认关门
ST_OPENING    = "OPENING"      # 正在开门(推杆缩回)
ST_OPEN       = "OPEN"         # 门已开, 等待人员进门
ST_CLOSING    = "CLOSING"      # 正在关门(推杆伸出)
ST_UNREG      = "UNREG"        # 非注册卡提示中


# ------------------------------------------------------------------ #
# 配置与注册卡
# ------------------------------------------------------------------ #
def load_config():
    default = {
        "mode": "demo",
        "cloud": {"base_url": "http://192.168.0.138",
                  "username": "18912345600", "password": "123456"},
        "device": {
            "device_id": 0,
            "rfid_tag": "m_uhf_epc",
            "travel_tag": "m_travelSwitch",      # 行程开关(关门确认)
            "near_tag": "m_near",                # 接近开关(开门确认)
            "laser_tag": "m_laser",              # 红外对射(人员进门)
            "pushrod_putt_tag": "m_pushrod_putt",   # 推杆前进(关门)
            "pushrod_back_tag": "m_pushrod_back",   # 推杆后退(开门)
            "led_display_tag": "m_led_text",         # LED 显示屏
        },
        "timeout_sec": 10,
        "unregistered_clear_sec": 5,
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


def load_cards():
    try:
        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ------------------------------------------------------------------ #
# 云服务读取(带 demo 模拟)
# ------------------------------------------------------------------ #
class CloudIO(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = None
        self.device_id = cfg["device"].get("device_id")
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
        """读传感器 0/1; RFID 读字符串; 读不到返回 None。"""
        if self.client is not None:
            try:
                v = self.client.fetch_sensor([tag], [self.device_id]) if hasattr(
                    self.client, "fetch_sensor") else None
                if v and tag in v and v[tag].get("value") is not None:
                    val = v[tag]["value"]
                    if tag == self.cfg["device"]["rfid_tag"]:
                        return str(val)
                    return 1 if float(val) >= 1.0 else 0
            except Exception:
                pass
            return None
        return None

    def write(self, tag, value):
        if self.client is not None:
            try:
                self.client.send_command(self.device_id, tag, value)
            except Exception:
                pass

    def write_text(self, tag, text):
        """LED 显示屏显示文本(通过云下发文本型执行器)。"""
        if self.client is not None:
            try:
                self.client.send_command(self.device_id, tag, text)
            except Exception:
                pass


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class AccessGateApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.cards = load_cards()
        self.io = CloudIO(self.cfg)
        self.d = self.cfg["device"]

        self.state = ST_CLOSED
        self.running = True
        self.last_rfid = None
        self.current_person = None     # 注册卡绑定人员
        self.person_status = "离岗"    # 离岗 / 在岗
        self.state_enter_tick = time.time()

        self.root.title(APP_NAME)
        self.root.geometry("820x560")
        self.root.configure(bg="#F4F6F8")

        self._build_ui()
        # 初始: 确保关门
        self._close_door()
        self._poll_loop()

    # ---------------- UI ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="智慧门禁系统 - 入口端",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#2E7D32", fg="white", pady=10).pack(fill="x")

        main = tk.Frame(self.root, bg="#F4F6F8")
        main.pack(fill="both", expand=True, padx=12, pady=8)

        # 左: 门状态 + 人员信息
        left = tk.Frame(main, bg="#F4F6F8")
        left.pack(side="left", fill="both", expand=True, padx=4)

        self.cv_door = tk.Canvas(left, width=300, height=220, bg="white",
                                 relief="ridge", bd=1)
        self.cv_door.pack(pady=6)

        self.lbl_state = tk.Label(left, text="门状态: 关门",
                                  font=("Microsoft YaHei", 14, "bold"),
                                  fg="#2E7D32", bg="#F4F6F8")
        self.lbl_state.pack(pady=2)

        self.lbl_person = tk.Label(left, text="人员: --",
                                   font=("Microsoft YaHei", 13), bg="#F4F6F8")
        self.lbl_person.pack(pady=2)

        self.lbl_status = tk.Label(left, text="人员状态: 离岗",
                                   font=("Microsoft YaHei", 13, "bold"),
                                   fg="#1565C0", bg="#F4F6F8")
        self.lbl_status.pack(pady=2)

        # 右: LED 显示屏 + 刷卡记录
        right = tk.LabelFrame(main, text="LED 显示屏 / 刷卡记录",
                              font=("Microsoft YaHei", 11))
        right.pack(side="right", fill="both", expand=True, padx=6)

        self.cv_led = tk.Canvas(right, width=300, height=80, bg="black",
                                relief="sunken", bd=2)
        self.cv_led.pack(pady=6)
        self.led_text_id = self.cv_led.create_text(150, 40, text="",
                                                   fill="#00FF00",
                                                   font=("Consolas", 16, "bold"))

        self.lbl_rfid = tk.Label(right, text="卡号: --",
                                 font=("Consolas", 10), bg="white", anchor="w")
        self.lbl_rfid.pack(fill="x", padx=8, pady=2)

        self.lbl_tip = tk.Label(self.root, text="状态: 等待刷卡...",
                                font=("Microsoft YaHei", 10), fg="#666")
        self.lbl_tip.pack(pady=4)

    # ---------------- 门控 ---------------- #
    def _open_door(self):
        """电动推杆缩回(后退) -> 开门。"""
        self.io.write(self.d["pushrod_back_tag"], 1)
        self.io.write(self.d["pushrod_putt_tag"], 0)

    def _close_door(self):
        """电动推杆伸出(前进) -> 关门。"""
        self.io.write(self.d["pushrod_putt_tag"], 1)
        self.io.write(self.d["pushrod_back_tag"], 0)

    def _led_show(self, text):
        self.cv_led.itemconfig(self.led_text_id, text=text)
        self.io.write_text(self.d["led_display_tag"], text)

    # ---------------- 状态机 ---------------- #
    def _set_state(self, s):
        self.state = s
        self.state_enter_tick = time.time()
        self._refresh_door_ui()

    def _refresh_door_ui(self):
        self.cv_door.delete("all")
        if self.state in (ST_CLOSED, ST_CLOSING):
            color = "#2E7D32"
            txt = "关门"
        elif self.state in (ST_OPENING, ST_OPEN):
            color = "#EF6C00"
            txt = "开门"
        else:
            color = "#C62828"
            txt = "未注册"
        self.cv_door.create_rectangle(20, 20, 280, 200, outline=color, width=4)
        self.cv_door.create_text(150, 110, text=txt, fill=color,
                                 font=("Microsoft YaHei", 24, "bold"))
        self.lbl_state.config(text="门状态: %s" % txt, fg=color)

    def _poll_loop(self):
        if not self.running:
            return
        try:
            self.step()
        except Exception as exc:
            self.lbl_tip.config(text="状态: %s" % exc)
        self.root.after(int(self.cfg["poll_interval_sec"]) * 1000, self._poll_loop)

    def step(self):
        d = self.d
        rfid = self.io.read(d["rfid_tag"])
        travel = self.io.read(d["travel_tag"])   # 行程开关(关门确认)
        near = self.io.read(d["near_tag"])       # 接近开关(开门确认)
        laser = self.io.read(d["laser_tag"])     # 红外对射(人员进门)

        elapsed = time.time() - self.state_enter_tick

        # 新刷卡(卡号变化且非空)
        if rfid and rfid != self.last_rfid and self.state in (ST_CLOSED,):
            self.last_rfid = rfid
            self.lbl_rfid.config(text="卡号: %s" % rfid)
            person = self.cards.get(rfid)
            if person:
                # 注册卡 -> 开门
                self.current_person = person
                self.person_status = "离岗"
                self.lbl_person.config(
                    text="人员: %s (%s)" % (person.get("name", "--"),
                                            person.get("dept", "--")))
                self.lbl_status.config(text="人员状态: 离岗")
                self._open_door()
                self._set_state(ST_OPENING)
            else:
                # 非注册卡 -> 不开门, LED 显示"未注册"
                self._led_show("未注册")
                self._set_state(ST_UNREG)

        # 状态迁移
        if self.state == ST_OPENING:
            # 接近开关确认门已开
            if near == 1:
                self._set_state(ST_OPEN)
        elif self.state == ST_OPEN:
            # 红外对射触发 -> 人员进门 -> 关门, 在岗, LED 显示"请带好安全帽"
            if laser == 1:
                self._close_door()
                self.person_status = "在岗"
                self.lbl_status.config(text="人员状态: 在岗")
                self._led_show("请带好安全帽")
                self._set_state(ST_CLOSING)
            elif elapsed >= float(self.cfg["timeout_sec"]):
                # 10 秒无人进门 -> 自动关门, 清人员, LED 无显示
                self._close_door()
                self.current_person = None
                self.lbl_person.config(text="人员: --")
                self._led_show("")
                self._set_state(ST_CLOSING)
        elif self.state == ST_CLOSING:
            # 行程开关确认门已关
            if travel == 1:
                self._set_state(ST_CLOSED)
                self.last_rfid = None
        elif self.state == ST_UNREG:
            # 5 秒后 LED 无显示, 回到关门
            if elapsed >= float(self.cfg["unregistered_clear_sec"]):
                self._led_show("")
                self._set_state(ST_CLOSED)
                self.last_rfid = None

    def on_close(self):
        self.running = False
        self._close_door()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AccessGateApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
