# -*- coding: utf-8 -*-
"""
商品管理功能（子任务2-7，第10套）

功能:
  1. 程序启动后读取已录入商品数据并显示在主界面, 按入库时间倒序排列。
  2. 支持按"商品名称"和"入库时间段"查询已录入商品(不分页)。
  3. 点击"商品入库"打开新页面录入新商品信息。
  4. 入库页"读取"按钮读取 UHF 超高频读写器数据, 自动填入"商品RFID"字段。
  5. 读取到已被使用的 RFID 时, 主界面红色字体提示并阻止录入, 同时工位报警灯亮起。
  6. 所有商品数据持久化保存(JSON)。

运行: python product_manage.py
"""
import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from nle_cloud import load_config, create_client

APP_NAME = "商品管理系统"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CFG = {
    "mode": "demo",
    "cloud_url": "http://192.168.0.138",
    "cloud_user": "18912345600",
    "cloud_pwd": "123456",
    "device_id": 1,
    "alarm_apitag": "m_rotating_lamp",
    "data_file": "products.json",
}


# ------------------------------------------------------------------ #
# 商品数据存储
# ------------------------------------------------------------------ #
class ProductStore(object):
    def __init__(self, path):
        self.path = path
        self.products = []
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.products = data
        except Exception:
            self.products = []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)

    def has_rfid(self, rfid):
        rfid = (rfid or "").strip()
        return any((p.get("rfid", "").strip() == rfid) for p in self.products)

    def add(self, product):
        self.products.append(product)
        self.save()

    def sorted_desc(self):
        return sorted(self.products,
                      key=lambda p: p.get("in_time", ""), reverse=True)


# ------------------------------------------------------------------ #
# UHF 读取器(串口服务器/云)
# ------------------------------------------------------------------ #
class RFIDReader(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.cloud = create_client(cfg["mode"], cfg["cloud_url"],
                                   cfg["cloud_user"], cfg["cloud_pwd"])
        self._idx = 0

    def read_epc(self):
        """返回读到的 EPC 字符串; 真实环境接入 nle_library GenericConnector.readSingleEpc。"""
        time.sleep(0.2)
        # 演示: 模拟轮播三个标签
        self._idx += 1
        pool = [
            "E280116060000209A000000001",
            "E280116060000209A000000002",
            "E280116060000209A000000003",
        ]
        return pool[self._idx % len(pool)]


# ------------------------------------------------------------------ #
# 入库子窗口
# ------------------------------------------------------------------ #
class InboundDialog(object):
    def __init__(self, master, store, reader, on_saved, on_dup):
        self.top = tk.Toplevel(master)
        self.top.title("商品入库")
        self.top.geometry("460x320")
        self.top.transient(master)
        self.store = store
        self.reader = reader
        self.on_saved = on_saved
        self.on_dup = on_dup

        frm = tk.Frame(self.top, padx=12, pady=12)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="商品RFID:", font=("Microsoft YaHei", 11)).grid(row=0, column=0, sticky="e", pady=4)
        self.var_rfid = tk.StringVar()
        tk.Entry(frm, textvariable=self.var_rfid, width=34, font=("Consolas", 10)).grid(row=0, column=1, pady=4)
        tk.Button(frm, text="读取", command=self.on_read).grid(row=0, column=2, padx=4)

        tk.Label(frm, text="商品名称:", font=("Microsoft YaHei", 11)).grid(row=1, column=0, sticky="e", pady=4)
        self.var_name = tk.StringVar()
        tk.Entry(frm, textvariable=self.var_name, width=34).grid(row=1, column=1, pady=4)

        tk.Label(frm, text="规格:", font=("Microsoft YaHei", 11)).grid(row=2, column=0, sticky="e", pady=4)
        self.var_spec = tk.StringVar()
        tk.Entry(frm, textvariable=self.var_spec, width=34).grid(row=2, column=1, pady=4)

        tk.Label(frm, text="单价(元):", font=("Microsoft YaHei", 11)).grid(row=3, column=0, sticky="e", pady=4)
        self.var_price = tk.StringVar()
        tk.Entry(frm, textvariable=self.var_price, width=34).grid(row=3, column=1, pady=4)

        self.var_msg = tk.StringVar(value="")
        self.lb_msg = tk.Label(frm, textvariable=self.var_msg, fg="#C62828",
                               font=("Microsoft YaHei", 10))
        self.lb_msg.grid(row=4, column=0, columnspan=3, pady=6)

        tk.Button(frm, text="确认入库", bg="#2E7D32", fg="white",
                  font=("Microsoft YaHei", 11), command=self.on_submit).grid(
            row=5, column=0, columnspan=3, pady=8)

    def on_read(self):
        def work():
            epc = self.reader.read_epc()
            self.top.after(0, lambda: self._after_read(epc))
        threading.Thread(target=work, daemon=True).start()

    def _after_read(self, epc):
        self.var_rfid.set(epc or "")
        if epc and self.store.has_rfid(epc):
            # 重复 RFID: 红字提示 + 报警灯亮
            self.var_msg.set("该RFID已被使用, 不允许重复入库!")
            self.on_dup(epc)

    def on_submit(self):
        rfid = self.var_rfid.get().strip()
        name = self.var_name.get().strip()
        spec = self.var_spec.get().strip()
        price = self.var_price.get().strip()
        if not rfid or not name:
            messagebox.showwarning(APP_NAME, "RFID与商品名称不能为空")
            return
        if self.store.has_rfid(rfid):
            self.var_msg.set("该RFID已被使用, 已阻止录入!")
            self.on_dup(rfid)
            return
        product = {
            "rfid": rfid,
            "name": name,
            "spec": spec,
            "price": price,
            "in_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.store.add(product)
        self.on_saved()
        self.top.destroy()


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class ProductApp(object):
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("860x520")
        self.cfg = load_config(CONFIG_PATH, DEFAULT_CFG)
        self.store = ProductStore(os.path.join(BASE_DIR, self.cfg["data_file"]))
        self.reader = RFIDReader(self.cfg)
        self.cloud = self.reader.cloud

        self._build_ui()
        self.refresh(self.store.sorted_desc())

    def _build_ui(self):
        tk.Label(self.root, text="商品管理系统", font=("Microsoft YaHei", 15, "bold"),
                 bg="#1565C0", fg="white", pady=8).pack(fill="x")

        # 查询区
        qf = tk.Frame(self.root, padx=8, pady=6)
        qf.pack(fill="x")
        tk.Label(qf, text="商品名称:").pack(side="left")
        self.var_qname = tk.StringVar()
        tk.Entry(qf, textvariable=self.var_qname, width=14).pack(side="left", padx=4)
        tk.Label(qf, text="入库起:").pack(side="left")
        self.var_qstart = tk.StringVar()
        tk.Entry(qf, textvariable=self.var_qstart, width=18).pack(side="left", padx=4)
        tk.Label(qf, text="止:").pack(side="left")
        self.var_qend = tk.StringVar()
        tk.Entry(qf, textvariable=self.var_qend, width=18).pack(side="left", padx=4)
        tk.Button(qf, text="查询", command=self.on_query).pack(side="left", padx=4)
        tk.Button(qf, text="重置", command=self.on_reset).pack(side="left")

        # 商品表
        cols = ("rfid", "name", "spec", "price", "in_time")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=14)
        self.tree.heading("rfid", text="商品RFID")
        self.tree.heading("name", text="商品名称")
        self.tree.heading("spec", text="规格")
        self.tree.heading("price", text="单价(元)")
        self.tree.heading("in_time", text="入库时间")
        self.tree.column("rfid", width=260)
        self.tree.column("name", width=120, anchor="center")
        self.tree.column("spec", width=140, anchor="center")
        self.tree.column("price", width=90, anchor="center")
        self.tree.column("in_time", width=160, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=4)

        # 状态/提示 + 入库按钮
        bf = tk.Frame(self.root, padx=8, pady=6)
        bf.pack(fill="x")
        self.var_status = tk.StringVar(value="")
        self.lb_status = tk.Label(bf, textvariable=self.var_status, fg="#C62828",
                                  font=("Microsoft YaHei", 11, "bold"))
        self.lb_status.pack(side="left")
        tk.Button(bf, text="商品入库", bg="#2E7D32", fg="white",
                  font=("Microsoft YaHei", 12), command=self.open_inbound).pack(side="right")

    def refresh(self, rows):
        self.tree.delete(*self.tree.get_children())
        for p in rows:
            self.tree.insert("", "end", values=(
                p.get("rfid", ""), p.get("name", ""), p.get("spec", ""),
                p.get("price", ""), p.get("in_time", "")))

    def on_query(self):
        name = self.var_qname.get().strip()
        start = self.var_qstart.get().strip()
        end = self.var_qend.get().strip()
        rows = self.store.sorted_desc()
        out = []
        for p in rows:
            if name and name not in p.get("name", ""):
                continue
            t = p.get("in_time", "")
            if start and t < start:
                continue
            if end and t > end:
                continue
            out.append(p)
        self.refresh(out)

    def on_reset(self):
        self.var_qname.set("")
        self.var_qstart.set("")
        self.var_qend.set("")
        self.refresh(self.store.sorted_desc())

    def open_inbound(self):
        InboundDialog(self.root, self.store, self.reader,
                      on_saved=lambda: (self.refresh(self.store.sorted_desc()),
                                        self._clear_alarm()),
                      on_dup=self._on_dup)

    def _on_dup(self, rfid):
        self.var_status.set("提示: RFID %s 已被使用, 已阻止录入! 报警灯已亮。" % rfid)
        self._set_alarm(True)

    def _clear_alarm(self):
        self.var_status.set("")
        self._set_alarm(False)

    def _set_alarm(self, on):
        try:
            self.cloud.send_command(int(self.cfg.get("device_id", 1)),
                                    self.cfg["alarm_apitag"], 1 if on else 0)
        except Exception:
            pass


def main():
    root = tk.Tk()
    ProductApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
