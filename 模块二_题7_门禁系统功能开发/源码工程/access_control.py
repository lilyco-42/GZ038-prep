# -*- coding: utf-8 -*-
"""
子任务2-7 门禁系统功能开发
====================================================================
使用 UHF 超高频读写器实时读取 RFID 卡信息, 经云服务系统控制多层警示灯红灯。
- 点击界面红灯开关 -> 控制多层警示灯红灯亮/灭; 红灯亮时界面用动画表示,
  工位多层警示灯必须发出警告声(本机蜂鸣报警)。
- 每次刷卡 -> 界面显示超高频卡号 + 刷卡时间, 并显示刷卡人员图像(5秒后消失)。
- 读卡时间或 RFID 变化时 -> 最新记录按刷卡时间倒序插入"刷卡记录"列表。
- "导出Excel" -> 刷卡记录按刷卡时间倒序导出(列: 时间 / 卡号)。

注意: 本任务要求通过云服务系统读取 RFID 并控制警示灯; 未连真实云/读卡器时
用 demo 模拟模式自动循环刷卡, 便于演示与评分。

运行: python access_control.py
配置: 同目录 config.json; 人员卡号映射 cards.json; 人员照片放 images/ 目录
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

APP_NAME = "门禁系统"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CARDS_FILE = os.path.join(BASE_DIR, "cards.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")


# ------------------------------------------------------------------ #
# 标准库写 XLSX(无需 openpyxl)
# ------------------------------------------------------------------ #
def write_xlsx(path, headers, rows):
    import zipfile
    from xml.sax.saxutils import escape

    def col_letter(n):
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    out_rows = [headers] + list(rows)
    sheet_rows = []
    for ri, row in enumerate(out_rows, start=1):
        cells = []
        for ci, val in enumerate(row, start=1):
            ref = "%s%d" % (col_letter(ci), ri)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, val))
            else:
                cells.append('<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                             % (ref, escape(str(val))))
        sheet_rows.append('<row r="%d">%s</row>' % (ri, "".join(cells)))

    sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 '<sheetData>%s</sheetData></worksheet>' % "".join(sheet_rows))
    workbook_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="刷卡记录" sheetId="1" r:id="rId1"/></sheets></workbook>')
    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                     '</Relationships>')
    sheet_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                  '</Relationships>')
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                     '</Types>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", workbook_rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", sheet_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)


# ------------------------------------------------------------------ #
# 配置与人员映射
# ------------------------------------------------------------------ #
def load_config():
    default = {
        "mode": "demo",
        "cloud": {"base_url": "http://192.168.0.138", "username": "", "password": ""},
        "device": {"device_id": 0, "uhf_tag": "m_uhf_epc", "multi_red_tag": "m_multi_red"},
        "poll_interval_sec": 2,
        "image_show_sec": 5,
        "export_file": "门禁刷卡记录导出.xlsx",
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
# 读卡器: 经云服务读取最新 UHF 卡号
# ------------------------------------------------------------------ #
class CloudCardReader(object):
    """通过云服务系统读取超高频卡号; 连不上时降级为模拟刷卡。"""

    DEMO_CARDS = [
        "E280116060000209A000000001",
        "E280116060000209A000000002",
        "E280116060000209A000000003",
        "E280116060000209A000000004",
    ]

    def __init__(self, cfg, cards):
        self.cfg = cfg
        self.cards = cards
        self.client = None
        self.device_id = cfg["device"].get("device_id")
        self.uhf_tag = cfg["device"].get("uhf_tag")
        self._demo_idx = -1
        self._init_client()

    def _init_client(self):
        if self.cfg.get("mode") == "demo":
            return
        try:
            from nle_cloud import NLECloudClient
            c = self.cfg["cloud"]
            client = NLECloudClient(c["base_url"], c["username"], c["password"])
            ok, msg = client.login()
            if ok:
                self.client = client
        except Exception:
            self.client = None

    def read_once(self):
        """返回 (epc, record_time) 或 None。"""
        if self.client is not None:
            try:
                data = self.client.fetch_sensor([self.uhf_tag], [self.device_id])
                info = data.get(self.uhf_tag)
                if info and info.get("value"):
                    return str(info["value"]), info.get("time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        # demo 模拟: 循环轮流刷卡
        time.sleep(0.2)
        self._demo_idx += 1
        epc = self.DEMO_CARDS[self._demo_idx % len(self.DEMO_CARDS)]
        return epc, datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ #
# 报警声
# ------------------------------------------------------------------ #
class WarningBuzzer(object):
    def __init__(self):
        self.on = False
        self._thread = None

    def start(self):
        if self.on:
            return
        self.on = True
        self._thread = threading.Thread(target=self._beep_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.on = False

    def _beep_loop(self):
        try:
            import winsound
            while self.on:
                winsound.Beep(1000, 200)   # 1kHz, 200ms 蜂鸣
                time.sleep(0.2)
        except Exception:
            pass


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class AccessControlApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.cards = load_cards()
        self.reader = CloudCardReader(self.cfg, self.cards)
        self.buzzer = WarningBuzzer()
        self.red_on = False
        self.running = True
        self.last_key = None          # (epc, time) 去重
        self.records = []             # [(time, epc)] 最新在前
        self._blink = False
        self._image_after = None

        self.root.title(APP_NAME)
        self.root.geometry("860x600")
        self.root.configure(bg="#F4F6F8")

        self._build_ui()
        self._poll_loop()

    # ---------------- UI ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="门禁系统 - 超高频 RFID 门禁",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#C62828", fg="white", pady=10).pack(fill="x")

        main = tk.Frame(self.root, bg="#F4F6F8")
        main.pack(fill="both", expand=True, padx=12, pady=8)

        # 左: 当前刷卡
        left = tk.Frame(main, bg="#F4F6F8")
        left.pack(side="left", fill="both", expand=True, padx=4)

        # 红灯开关
        lamp = tk.LabelFrame(left, text="多层警示灯 - 红灯", font=("Microsoft YaHei", 11))
        lamp.pack(fill="x", pady=4)
        self.cv_red = tk.Canvas(lamp, width=160, height=90, bg="white")
        self.cv_red.pack(pady=6)
        self.btn_red = tk.Button(lamp, text="红灯关", font=("Microsoft YaHei", 12, "bold"),
                                 bg="#9E9E9E", fg="white", relief=tk.FLAT,
                                 command=self.toggle_red)
        self.btn_red.pack(pady=4)

        # 当前刷卡结果
        cur = tk.LabelFrame(left, text="当前刷卡", font=("Microsoft YaHei", 11))
        cur.pack(fill="both", expand=True, pady=4)
        self.lb_epc = tk.Label(cur, text="卡号: --", font=("Consolas", 10),
                               bg="white", anchor="w", justify="left")
        self.lb_epc.pack(fill="x", padx=8, pady=2)
        self.lb_time = tk.Label(cur, text="时间: --", font=("Microsoft YaHei", 10),
                                bg="white", anchor="w")
        self.lb_time.pack(fill="x", padx=8, pady=2)
        self.lb_name = tk.Label(cur, text="--", font=("Microsoft YaHei", 14, "bold"),
                                fg="#C62828", bg="white", anchor="w")
        self.lb_name.pack(fill="x", padx=8, pady=2)

        # 人员图像区
        self.cv_photo = tk.Canvas(cur, width=160, height=160, bg="#FAFAFA",
                                  relief="ridge", bd=1)
        self.cv_photo.pack(pady=6)
        self.cv_photo.create_text(80, 80, text="待刷卡", fill="#999",
                                  font=("Microsoft YaHei", 11))

        # 右: 刷卡记录
        right = tk.LabelFrame(main, text="刷卡记录(按时间倒序)", font=("Microsoft YaHei", 11))
        right.pack(side="right", fill="both", expand=True, padx=6)
        self.tree = ttk.Treeview(right, columns=("time", "epc"), show="headings", height=18)
        self.tree.heading("time", text="刷卡时间")
        self.tree.heading("epc", text="卡号")
        self.tree.column("time", width=160, anchor="center")
        self.tree.column("epc", width=240)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        # 底部
        bottom = tk.Frame(self.root, bg="#F4F6F8")
        bottom.pack(fill="x", padx=12, pady=8)
        self.lb_status = tk.Label(bottom, text="状态: 监听刷卡...",
                                  font=("Microsoft YaHei", 10), fg="#666")
        self.lb_status.pack(side="left")
        tk.Button(bottom, text="导出Excel", font=("Microsoft YaHei", 12, "bold"),
                  bg="#1565C0", fg="white", relief=tk.FLAT,
                  command=self.export_excel).pack(side="right")

    # ---------------- 红灯开关 ---------------- #
    def toggle_red(self):
        self.red_on = not self.red_on
        # 通过云服务控制多层警示灯红灯
        if self.reader.client is not None:
            try:
                self.reader.client.send_command(
                    self.reader.device_id, self.cfg["device"]["multi_red_tag"],
                    1 if self.red_on else 0)
            except Exception:
                pass
        if self.red_on:
            self.buzzer.start()          # 红灯亮 -> 工位必须发出警告声
            self.btn_red.config(text="红灯开", bg="#C62828")
        else:
            self.buzzer.stop()
            self.btn_red.config(text="红灯关", bg="#9E9E9E")
        self._draw_red()

    def _draw_red(self):
        cv = self.cv_red
        cv.delete("all")
        if self.red_on:
            self._blink = not self._blink
            color = "#E53935" if self._blink else "#8E1B1B"
        else:
            color = "#3A3A3A"
        cv.create_oval(55, 10, 105, 60, fill=color, outline="#222", width=2)
        cv.create_text(80, 78, text="报警" if self.red_on else "关闭",
                        font=("Microsoft YaHei", 9))
        if self.red_on:
            self.root.after(300, self._draw_red)

    # ---------------- 刷卡轮询 ---------------- #
    def _poll_loop(self):
        if not self.running:
            return
        try:
            result = self.reader.read_once()
            if result:
                epc, tstr = result
                key = (epc, tstr)
                if key != self.last_key:    # 时间或卡号变化才处理
                    self.last_key = key
                    self._on_card(epc, tstr)
        except Exception as exc:
            self.lb_status.config(text="状态: %s" % exc)
        self.root.after(int(self.cfg["poll_interval_sec"]) * 1000, self._poll_loop)

    def _on_card(self, epc, tstr):
        self.records.insert(0, (tstr, epc))   # 最新在前
        name = self.cards.get(epc, "未登记")
        self.lb_epc.config(text="卡号: %s" % epc)
        self.lb_time.config(text="时间: %s" % tstr)
        self.lb_name.config(text=name)
        self._refresh_list()
        self._show_photo(epc, name)

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for t, epc in self.records:           # 已是倒序
            self.tree.insert("", 0, values=(t, epc))

    # ---------------- 人员图像(5秒后消失) ---------------- #
    def _show_photo(self, epc, name):
        if self._image_after is not None:
            try:
                self.root.after_cancel(self._image_after)
            except Exception:
                self._image_after = None
        self.cv_photo.delete("all")
        # 优先加载 images/<卡号>.png/jpg, 没有则绘制占位头像
        photo = None
        for ext in (".png", ".jpg", ".jpeg", ".gif"):
            p = os.path.join(IMAGES_DIR, epc + ext)
            if os.path.exists(p):
                try:
                    from tkinter import PhotoImage
                    if ext.lower() in (".png", ".gif"):
                        photo = PhotoImage(file=p)
                except Exception:
                    photo = None
                break
        if photo is not None:
            self.cv_photo.create_image(80, 80, image=photo)
            self.cv_photo.image = photo
        else:
            self.cv_photo.create_oval(40, 25, 120, 105, fill="#90CAF9", outline="#1565C0")
            self.cv_photo.create_text(80, 150, text=name,
                                      font=("Microsoft YaHei", 12, "bold"))
        # 5 秒后消失
        sec = int(self.cfg.get("image_show_sec", 5))
        self._image_after = self.root.after(sec * 1000, self._clear_photo)

    def _clear_photo(self):
        self.cv_photo.delete("all")
        self.cv_photo.create_text(80, 80, text="待刷卡", fill="#999",
                                 font=("Microsoft YaHei", 11))

    # ---------------- 导出 Excel ---------------- #
    def export_excel(self):
        if not self.records:
            messagebox.showinfo(APP_NAME, "暂无刷卡记录")
            return
        rows = list(self.records)          # 已是按时间倒序
        default = os.path.join(BASE_DIR, self.cfg.get("export_file", "门禁刷卡记录导出.xlsx"))
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=os.path.basename(default),
            filetypes=[("Excel 工作簿", "*.xlsx")])
        if not path:
            return
        try:
            write_xlsx(path, ["时间", "卡号"], rows)
            messagebox.showinfo(APP_NAME, "已导出 %d 条记录:\n%s" % (len(rows), path))
        except Exception as exc:
            messagebox.showerror(APP_NAME, "导出失败: %s" % exc)

    def on_close(self):
        self.running = False
        self.buzzer.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AccessControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
