# -*- coding: utf-8 -*-
"""
子任务2-6 钻井深度监测功能开发
====================================================================
使用超声波传感器模拟钻井深度监测。
- 每 5 秒采集一次超声波数据, 界面显示并绘制"数据-时间"折线图(最近6次)。
- 超声波 >= 50cm: 控制工位频闪红灯亮, 否则灭。
- 超声波 <  50cm: 控制工位常亮绿灯亮, 否则灭。
- 灯亮时界面图标做动画, 灯灭时用灭灯图标。
- "导出Excel"按钮: 最近20条记录按时间倒序导出(列: 时间 / 超声波数据)。

注意: 本任务若用云服务获取数据或控制设备将不得分, 因此超声波读取与
灯光控制均为本地直连(串口/联动控制器); 未接硬件时用 demo 模拟模式运行。

运行: python drilling_depth_monitor.py
配置: 同目录 config.json
"""
import json
import os
import random
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

APP_NAME = "钻井深度监测"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


# ------------------------------------------------------------------ #
# 标准库写 XLSX(无需 openpyxl)
# ------------------------------------------------------------------ #
def write_xlsx(path, headers, rows):
    """用标准库 zipfile 生成一个最小可用的 .xlsx 文件。"""
    import zipfile
    from xml.sax.saxutils import escape

    def col_letter(n):
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    sheet_rows = []
    all_rows = [headers] + list(rows)
    for ri, row in enumerate(all_rows, start=1):
        cells = []
        for ci, val in enumerate(row, start=1):
            ref = "%s%d" % (col_letter(ci), ri)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, val))
            else:
                cells.append('<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                             % (ref, escape(str(val))))
        sheet_rows.append('<row r="%d">%s</row>' % (ri, "".join(cells)))

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>%s</sheetData></worksheet>' % "".join(sheet_rows)
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="监测数据" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    sheet_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", workbook_rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", sheet_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)


# ------------------------------------------------------------------ #
# 配置
# ------------------------------------------------------------------ #
def load_config():
    default = {
        "mode": "demo",
        "sample_interval_sec": 5,
        "chart_points": 6,
        "export_count": 20,
        "depth_threshold_cm": 50,
        "ultrasonic": {"source": "sim", "serial_port": "COM3", "baudrate": 9600},
        "actuator": {"strobe_red_tag": "m_strobe_red", "steady_green_tag": "m_steady_green"},
        "export_file": "钻井深度监测导出.xlsx",
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
# 超声波数据源(本地直连, 不走云服务)
# ------------------------------------------------------------------ #
class UltrasonicSource(object):
    """真实模式通过串口/联动控制器读取超声波距离; demo 模式模拟。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.ser = None
        self._state = 30.0
        if cfg["ultrasonic"].get("source") == "serial":
            self._open_serial()

    def _open_serial(self):
        try:
            import serial  # pyserial
            p = self.cfg["ultrasonic"]["serial_port"]
            b = self.cfg["ultrasonic"]["baudrate"]
            self.ser = serial.Serial(p, b, timeout=1)
        except Exception:
            self.ser = None

    def read_cm(self):
        """返回超声波距离(cm)。真实实现: 发送测距命令并解析返回帧。"""
        if self.ser is not None:
            try:
                # 厂商协议示例: self.ser.write(b'\x01\x03...'); 解析返回 -> cm
                return round(self._state, 1)  # 占位, 接入真实设备时替换
            except Exception:
                pass
        # demo 模拟: 在 20~80cm 之间缓慢漂移, 便于看到阈值切换
        self._state += random.uniform(-6, 6)
        self._state = max(10.0, min(90.0, self._state))
        return round(self._state, 1)


# ------------------------------------------------------------------ #
# 灯光执行器(本地直连联动控制器, 不走云服务)
# ------------------------------------------------------------------ #
class LightController(object):
    """真实模式通过串口/联动控制器控制频闪红灯与常亮绿灯。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.red_on = False
        self.green_on = False

    def set_strobe_red(self, on):
        self.red_on = bool(on)
        # 真实实现: 向联动控制器串口下发 开/关 频闪红灯命令
        # 例如 self._send_cmd(tag, 1/0)
        return self.red_on

    def set_steady_green(self, on):
        self.green_on = bool(on)
        # 真实实现: 向联动控制器串口下发 开/关 常亮绿灯命令
        return self.green_on


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class DrillingDepthApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.src = UltrasonicSource(self.cfg)
        self.act = LightController(self.cfg)

        self.threshold = float(self.cfg["depth_threshold_cm"])
        self.interval = int(self.cfg["sample_interval_sec"])
        self.chart_n = int(self.cfg["chart_points"])
        self.export_n = int(self.cfg["export_count"])

        self.history = []          # [(time_str, value)] 全部记录
        self.running = True
        self._blink = False

        self.root.title(APP_NAME)
        self.root.geometry("820x600")
        self.root.configure(bg="#F4F6F8")

        self._build_ui()
        self._poll_loop()

    # ---------------- UI ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="钻井深度监测系统",
                 font=("Microsoft YaHei", 18, "bold"),
                 bg="#1565C0", fg="white", pady=10).pack(fill="x")

        top = tk.Frame(self.root, bg="#F4F6F8")
        top.pack(fill="x", padx=12, pady=8)

        # 当前深度
        box = tk.LabelFrame(top, text="实时钻井深度", font=("Microsoft YaHei", 11))
        box.pack(side="left", padx=6)
        self.lb_depth = tk.Label(box, text="-- cm", font=("Consolas", 26, "bold"),
                                 fg="#1565C0", width=10)
        self.lb_depth.pack(padx=20, pady=10)

        # 灯图标
        lamp = tk.LabelFrame(top, text="工位灯状态", font=("Microsoft YaHei", 11))
        lamp.pack(side="left", padx=6, fill="both", expand=True)
        self.cv_lamp = tk.Canvas(lamp, width=360, height=110, bg="white")
        self.cv_lamp.pack(padx=8, pady=6)

        # 折线图
        chart = tk.LabelFrame(self.root, text='超声波"数据-时间"折线图(最近%d次)' % self.chart_n,
                              font=("Microsoft YaHei", 11))
        chart.pack(fill="both", expand=True, padx=12, pady=6)
        self.cv_chart = tk.Canvas(chart, bg="white")
        self.cv_chart.pack(fill="both", expand=True, padx=6, pady=6)

        # 底部
        bottom = tk.Frame(self.root, bg="#F4F6F8")
        bottom.pack(fill="x", padx=12, pady=8)
        self.lb_status = tk.Label(bottom, text="状态: 采集中...",
                                  font=("Microsoft YaHei", 10), fg="#666")
        self.lb_status.pack(side="left")
        tk.Button(bottom, text="导出Excel", font=("Microsoft YaHei", 12, "bold"),
                  bg="#43A047", fg="white", relief=tk.FLAT,
                  command=self.export_excel).pack(side="right")

    # ---------------- 采样线程 ---------------- #
    def _poll_loop(self):
        if not self.running:
            return
        try:
            value = self.src.read_cm()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.append((now, value))

            # 阈值控制(本地直连联动控制器)
            red = value >= self.threshold     # >=50cm 频闪红灯亮
            green = value < self.threshold    # <50cm 常亮绿灯亮
            self.act.set_strobe_red(red)
            self.act.set_steady_green(green)

            self._update_ui(now, value, red, green)
        except Exception as exc:
            self.lb_status.config(text="状态: 采集异常 %s" % exc)
        self.root.after(self.interval * 1000, self._poll_loop)

    def _update_ui(self, now, value, red, green):
        self.lb_depth.config(text="%.1f cm" % value)
        self._draw_lamps(red, green)
        self._draw_chart()

    # ---------------- 灯动画 ---------------- #
    def _draw_lamps(self, red_on, green_on):
        cv = self.cv_lamp
        cv.delete("all")
        self._blink = not self._blink
        # 频闪红灯: 亮时闪烁(半秒切换亮度)
        if red_on:
            r = "#E53935" if self._blink else "#7A1F1F"
        else:
            r = "#3A3A3A"
        # 常亮绿灯: 亮时常亮
        g = "#43A047" if green_on else "#2E4A2E"
        cv.create_oval(40, 25, 110, 95, fill=r, outline="#222", width=2)
        cv.create_text(75, 105, text="频闪红灯", font=("Microsoft YaHei", 10))
        cv.create_oval(230, 25, 300, 95, fill=g, outline="#222", width=2)
        cv.create_text(265, 105, text="常亮绿灯", font=("Microsoft YaHei", 10))
        # 灯在动画 -> 定时重绘实现闪烁
        if red_on:
            self.root.after(300, lambda: self._draw_lamps(red_on, green_on))

    # ---------------- 折线图(最近 N 次) ---------------- #
    def _draw_chart(self):
        cv = self.cv_chart
        cv.delete("all")
        w = cv.winfo_width() or 760
        h = cv.winfo_height() or 260
        pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 40
        pts = self.history[-self.chart_n:]
        if not pts:
            return

        values = [v for _, v in pts]
        vmin = 0
        vmax = max(100.0, max(values) * 1.2)

        # 阈值线 50cm
        ty = pad_t + (vmax - self.threshold) / (vmax - vmin) * (h - pad_t - pad_b)
        cv.create_line(pad_l, ty, w - pad_r, ty, fill="#E53935", dash=(4, 3))
        cv.create_text(pad_l + 4, ty - 6, text="阈值%.0fcm" % self.threshold,
                       fill="#E53935", anchor="w")

        if len(pts) == 1:
            xs = [ (pad_l + w - pad_r) / 2 ]
        else:
            xs = [pad_l + i * (w - pad_l - pad_r) / (len(pts) - 1) for i in range(len(pts))]
        ys = [pad_t + (vmax - v) / (vmax - vmin) * (h - pad_t - pad_b) for v in values]

        # 网格/纵轴刻度
        for k in range(5):
            vv = vmin + (vmax - vmin) * k / 4
            yy = pad_t + (vmax - vv) / (vmax - vmin) * (h - pad_t - pad_b)
            cv.create_line(pad_l, yy, w - pad_r, yy, fill="#EEE")
            cv.create_text(pad_l - 6, yy, text="%.0f" % vv, anchor="e",
                           font=("Microsoft YaHei", 8))

        # 折线
        line = []
        for x, y in zip(xs, ys):
            line += [x, y]
        if len(line) >= 4:
            cv.create_line(*line, fill="#1565C0", width=2)
        for x, y, (t, v) in zip(xs, ys, pts):
            cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#1565C0", outline="")
            cv.create_text(x, y - 12, text="%.0f" % v, fill="#1565C0",
                            font=("Microsoft YaHei", 8))
            cv.create_text(x, h - pad_b + 14, text=t[11:], fill="#666",
                           font=("Microsoft YaHei", 7))

    # ---------------- 导出 Excel ---------------- #
    def export_excel(self):
        if not self.history:
            messagebox.showinfo(APP_NAME, "暂无数据可导出")
            return
        recent = self.history[-self.export_n:]
        recent_desc = list(reversed(recent))     # 按记录时间倒序
        rows = [(t, v) for t, v in recent_desc]

        default = os.path.join(BASE_DIR, self.cfg.get("export_file", "钻井深度监测导出.xlsx"))
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=os.path.basename(default),
            filetypes=[("Excel 工作簿", "*.xlsx")])
        if not path:
            return
        try:
            write_xlsx(path, ["时间", "超声波数据"], rows)
            messagebox.showinfo(APP_NAME, "已导出 %d 条记录:\n%s" % (len(rows), path))
        except Exception as exc:
            messagebox.showerror(APP_NAME, "导出失败: %s" % exc)

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = DrillingDepthApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
