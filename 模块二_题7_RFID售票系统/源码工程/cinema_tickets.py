# -*- coding: utf-8 -*-
"""
动感影院 RFID 售票系统（2-7 / GZ038 第3套）

假定影院共 10 个 4D 座席：
  1. 买票时指定空闲座席，用超高频(UHF)桌面读卡器读取标签并绑定到座位号；
     绑定即代表票已售出，是否入座默认为“否”。
  2. 售出但未入座的票，界面显示“退票”按钮；已入座的不再显示退票按钮。
  3. 点“退票”-> 确认后该记录 RFID 清空，是否售出=否、是否入座=否，已售数 -1。
  4. 用 UHF 读写器读取 RFID 模拟检票：自动把对应座位是否入座改为“是”，已就座数 +1。
  5. 自动统计已售出、已就座数量。

运行: python cinema_tickets.py
依赖: Python 3.x, tkinter, json（标准库）。UHF 读卡器走串口/SDK。
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "动感影院售票"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config():
    cfg = {"total_seats": 10,
           "uhf": {"port": "COM3", "baud": 115200, "mode": "simulate"},
           "data_file": "seat_tickets.json"}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


# ------------------------------------------------------------------ #
# 座席数据
# ------------------------------------------------------------------ #
class SeatStore:
    def __init__(self, path, total=10):
        self.path = path
        self.total = total
        # seats: list of dict {seat, rfid, sold, seated}
        self.seats = [{"seat": i + 1, "rfid": "", "sold": False, "seated": False}
                      for i in range(total)]
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for row in data:
                        s = row.get("seat")
                        if isinstance(s, int) and 1 <= s <= self.total:
                            self.seats[s - 1].update(
                                rfid=row.get("rfid", ""),
                                sold=bool(row.get("sold", False)),
                                seated=bool(row.get("seated", False)))
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.seats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def sold_count(self):
        return sum(1 for s in self.seats if s["sold"])

    def seated_count(self):
        return sum(1 for s in self.seats if s["seated"])

    def find_by_rfid(self, rfid):
        rfid = (rfid or "").strip().upper()
        for s in self.seats:
            if s["rfid"] and s["rfid"].upper() == rfid:
                return s
        return None


# ------------------------------------------------------------------ #
# UHF 读卡器
# ------------------------------------------------------------------ #
class SimulatedUHF:
    """模拟 UHF：轮询返回已绑定标签，便于无硬件演示。"""

    def __init__(self, store):
        self.store = store
        self._i = 0

    def read_tag(self):
        time.sleep(0.2)
        sold = [s for s in self.store.seats if s["sold"]]
        if not sold:
            return None
        self._i += 1
        return sold[self._i % len(sold)]["rfid"]


class SerialUHF:
    """真实 UHF 读写器（串口/SDK）。现场按厂商协议实现 read_tag。"""

    def __init__(self, port="COM3", baud=115200):
        self.port = port
        self.baud = baud

    def read_tag(self):
        # import serial
        # ser = serial.Serial(self.port, self.baud, timeout=0.5)
        # ser.write(<读标签指令帧>)
        # resp = ser.read(...)
        # return <解析出的 EPC>
        return None


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class CinemaTicketApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.store = SeatStore(os.path.join(BASE_DIR, self.cfg.get("data_file", "seat_tickets.json")),
                               int(self.cfg.get("total_seats", 10)))

        mode = self.cfg.get("uhf", {}).get("mode", "simulate")
        self.reader = SimulatedUHF(self.store) if mode == "simulate" \
            else SerialUHF(self.cfg["uhf"]["port"], int(self.cfg["uhf"]["baud"]))

        self.running = False
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        self.root.title(APP_NAME)
        self.root.geometry("820x540")
        self.root.configure(bg="#221133")

        tk.Label(self.root, text="动感影院 · 4D 座席 RFID 售票",
                 font=("Microsoft YaHei", 16, "bold"),
                 bg="#221133", fg="#FFC107", pady=8).pack(fill="x")

        # 统计
        stat = tk.Frame(self.root, bg="#221133")
        stat.pack(fill="x", padx=10)
        self.lb_sold = tk.Label(stat, text="已售出: 0", font=("Microsoft YaHei", 13, "bold"),
                                bg="#221133", fg="#4CAF50")
        self.lb_sold.pack(side="left", padx=20)
        self.lb_seated = tk.Label(stat, text="已就座: 0", font=("Microsoft YaHei", 13, "bold"),
                                  bg="#221133", fg="#2196F3")
        self.lb_seated.pack(side="right", padx=20)

        # 座席表
        cols = ("seat", "rfid", "sold", "seated")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=12)
        self.tree.heading("seat", text="座席")
        self.tree.heading("rfid", text="RFID 标签")
        self.tree.heading("sold", text="是否售出")
        self.tree.heading("seated", text="是否入座")
        self.tree.column("seat", width=80, anchor="center")
        self.tree.column("rfid", width=320, anchor="center")
        self.tree.column("sold", width=100, anchor="center")
        self.tree.column("seated", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # 当前选中座席的退票按钮区
        self.btn_row = tk.Frame(self.root, bg="#221133")
        self.btn_row.pack(fill="x", padx=10, pady=4)

        self.btn_bind = tk.Button(self.btn_row, text="绑定RFID售票",
                                   font=("Microsoft YaHei", 11, "bold"),
                                   bg="#4CAF50", fg="white", relief=tk.FLAT,
                                   command=self.bind_ticket)
        self.btn_bind.pack(side="left", fill="x", expand=True, padx=3)

        self.btn_refund = tk.Button(self.btn_row, text="退票",
                                    font=("Microsoft YaHei", 11, "bold"),
                                    bg="#F44336", fg="white", relief=tk.FLAT,
                                    command=self.refund_ticket, state=tk.DISABLED)
        self.btn_refund.pack(side="left", fill="x", expand=True, padx=3)

        self.btn_ckeck = tk.Button(self.btn_row, text="开始检票读RFID",
                                    font=("Microsoft YaHei", 11, "bold"),
                                    bg="#FF9800", fg="white", relief=tk.FLAT,
                                    command=self.toggle_check)
        self.btn_ckeck.pack(side="left", fill="x", expand=True, padx=3)

        self.var_status = tk.StringVar(value="状态: 请选择空闲座席后绑定RFID")
        tk.Label(self.root, textvariable=self.var_status,
                 font=("Microsoft YaHei", 10), bg="#221133", fg="#CCCCCC").pack()

        self.selected = None  # 当前选中座席号

    # ---------------- 刷新 ---------------- #
    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for s in self.store.seats:
            self.tree.insert("", tk.END, iid=str(s["seat"]),
                             values=("4D-%02d" % s["seat"],
                                     s["rfid"] or "（未绑定）",
                                     "是" if s["sold"] else "否",
                                     "是" if s["seated"] else "否"))
        self.lb_sold.config(text="已售出: %d" % self.store.sold_count())
        self.lb_seated.config(text="已就座: %d" % self.store.seated_count())
        self._update_refund_btn()
        self.store.save()

    def _on_select(self, _evt):
        sel = self.tree.selection()
        self.selected = int(sel[0]) if sel else None
        self._update_refund_btn()

    def _update_refund_btn(self):
        """仅“售出且未入座”的票显示退票按钮。"""
        if self.selected is None:
            self.btn_refund.config(state=tk.DISABLED)
            return
        s = self.store.seats[self.selected - 1]
        if s["sold"] and not s["seated"]:
            self.btn_refund.config(state=tk.NORMAL)
        else:
            self.btn_refund.config(state=tk.DISABLED)

    # ---------------- 售票绑定 ---------------- #
    def bind_ticket(self):
        if self.selected is None:
            messagebox.showinfo(APP_NAME, "请先在表中选择一个空闲座席")
            return
        s = self.store.seats[self.selected - 1]
        if s["sold"]:
            messagebox.showinfo(APP_NAME, "该座席已售出，请选择其它空闲座席")
            return
        self.var_status.set("请把 RFID 标签放在读写区...")
        self.root.update()
        tag = self.reader.read_tag()
        if not tag:
            messagebox.showwarning(APP_NAME, "未读到 RFID 标签")
            self.var_status.set("状态: 读标签失败")
            return
        s["rfid"] = tag.strip().upper()
        s["sold"] = True
        s["seated"] = False
        self.var_status.set("状态: 座席 4D-%02d 已绑定并售出" % s["seat"])
        self._refresh()

    # ---------------- 退票 ---------------- #
    def refund_ticket(self):
        s = self.store.seats[self.selected - 1]
        if not messagebox.askyesno("退票确认",
                                   "确认退掉座席 4D-%02d 的票？\nRFID 将清空，是否入座置否。" % s["seat"]):
            return
        s["rfid"] = ""
        s["sold"] = False
        s["seated"] = False
        self.var_status.set("状态: 座席 4D-%02d 已退票" % s["seat"])
        self._refresh()

    # ---------------- 检票 ---------------- #
    def toggle_check(self):
        if self.running:
            self.running = False
            self.btn_ckeck.config(text="开始检票读RFID")
            return
        self.running = True
        self.btn_ckeck.config(text="停止检票")
        threading.Thread(target=self._check_loop, daemon=True).start()

    def _check_loop(self):
        last = None
        while self.running:
            try:
                tag = self.reader.read_tag()
                if tag and tag != last:
                    last = tag
                    self.root.after(0, lambda t=tag: self._on_check(t))
                time.sleep(0.2)
            except Exception:
                time.sleep(0.3)

    def _on_check(self, tag):
        s = self.store.find_by_rfid(tag)
        if s is None:
            self.var_status.set("状态: 未知标签 %s" % tag)
            return
        if not s["sold"]:
            self.var_status.set("状态: 该标签未售票")
            return
        s["seated"] = True   # UHF 读到即检票入座
        self.var_status.set("状态: 检票通过，座席 4D-%02d 已就座" % s["seat"])
        self._refresh()


def main():
    root = tk.Tk()
    CinemaTicketApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
