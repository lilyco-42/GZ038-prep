# -*- coding: utf-8 -*-
"""
门闸环境系统（子任务2-6，第10套）

功能:
  1. 实时显示 温度/湿度/CO2/噪声(串口服务器TCP经网关上报云), 每5秒自动落盘(sqlite)。
  2. 程序运行时门=关(电动推杆伸出最长 m_pushrod_putt=1)。
  3. 开门/关门按钮控制闸门, 界面有闸门动画。
  4. 中间实时显示大厅监控画面, 支持上下左右云台控制。
  5. "截图"保存当前画面; "图片列表"弹出已截图列表可返回首页;
     "历史记录"按类型(温度/湿度/CO2/噪声)+起止时间过滤, 结果按记录时间倒序, 可返回首页。

数据从串口服务器 TCP 模式获取(经中心网关上报云, 本程序通过 nle_cloud 读取)。
摄像头: 配置 snapshot/ptz URL 时用 urllib 拉取; 失败或未配置时自动降级模拟画面。
运行: python gate_env.py
"""
import json
import os
import sqlite3
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox
from urllib import request as _urlrequest

from nle_cloud import load_config, create_client

APP_NAME = "门闸环境监控系统"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CFG = {
    "mode": "demo",
    "cloud_url": "http://192.168.0.138",
    "cloud_user": "18912345600",
    "cloud_pwd": "123456",
    "device_id": 1,
    "tags": {"temp": "m_temp", "hum": "m_hum", "co2": "m_co2", "noise": "m_noise"},
    "door": {"putt_tag": "m_pushrod_putt", "back_tag": "m_pushrod_back"},
    "camera": {"ip": "", "port": 80, "user": "admin", "pass": "",
               "snapshot_url": "http://{ip}:{port}/snapshot.jpg",
               "ptz_url": "http://{ip}:{port}/ptz_control.cgi?cmd={dir}&user={user}&pwd={pass}"},
    "save_interval_sec": 5,
    "db_file": "gate_env.db",
    "snapshot_dir": "snapshots",
}

# 可选依赖 Pillow(用于监控帧显示与截图保存), 缺失时降级为纯色占位
try:
    from PIL import Image, ImageDraw, ImageTk  # noqa
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


# ------------------------------------------------------------------ #
# 数据存储(sqlite)
# ------------------------------------------------------------------ #
class EnvDB(object):
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS logs("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "time TEXT, temp REAL, hum REAL, co2 REAL, noise REAL)")
        self.conn.commit()

    def insert(self, temp, hum, co2, noise):
        with self.lock:
            self.conn.execute(
                "INSERT INTO logs(time,temp,hum,co2,noise) VALUES(?,?,?,?,?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 temp, hum, co2, noise))
            self.conn.commit()

    def query(self, type_, start, end):
        """按类型+起止时间过滤, 按记录时间倒序。"""
        col = {"temp": "temp", "hum": "hum", "co2": "co2",
               "noise": "noise"}.get(type_, None)
        sql = "SELECT time, "
        select = col if col else "temp,hum,co2,noise"
        sql += select + " FROM logs WHERE 1=1"
        args = []
        if start:
            sql += " AND time>=?"; args.append(start)
        if end:
            sql += " AND time<=?"; args.append(end)
        sql += " ORDER BY time DESC"
        with self.lock:
            cur = self.conn.execute(sql, args)
            rows = cur.fetchall()
        return rows, col


# ------------------------------------------------------------------ #
# 监控画面(模拟 / 真实快照)
# ------------------------------------------------------------------ #
class CameraCtrl(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.cam = cfg["camera"]
        self._n = 0

    def snapshot_frame(self):
        """返回 PIL Image; 失败返回 None。"""
        ip = self.cam.get("ip", "")
        if HAVE_PIL and ip:
            try:
                url = self._url(self.cam.get("snapshot_url", ""), None)
                with _urlrequest.urlopen(url, timeout=3) as r:
                    data = r.read()
                from PIL import Image
                import io
                return Image.open(io.BytesIO(data)).convert("RGB")
            except Exception:
                pass
        return self._sim_frame()

    def ptz(self, direction):
        ip = self.cam.get("ip", "")
        if not ip:
            return False
        try:
            url = self._url(self.cam.get("ptz_url", ""), direction)
            with _urlrequest.urlopen(url, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def _url(self, tmpl, direction):
        u = (tmpl or "").replace("{ip}", str(self.cam.get("ip", ""))) \
                        .replace("{port}", str(self.cam.get("port", 80))) \
                        .replace("{user}", str(self.cam.get("user", ""))) \
                        .replace("{pass}", str(self.cam.get("pass", "")))
        if direction:
            u = u.replace("{dir}", direction)
        return u

    def _sim_frame(self, w=480, h=300):
        if not HAVE_PIL:
            return None
        from PIL import Image, ImageDraw
        self._n += 1
        img = Image.new("RGB", (w, h), (8, 18, 30))
        d = ImageDraw.Draw(img)
        for x in range(0, w, 40):
            d.line([(x, 0), (x, h)], fill=(18, 38, 60))
        for y in range(0, h, 40):
            d.line([(0, y), (w, y)], fill=(18, 38, 60))
        if self._n % 30 < 22:
            d.ellipse([14, 12, 30, 28], fill=(220, 40, 40))
            d.text((36, 12), "REC", fill=(230, 60, 60))
        d.text((w - 190, 12), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               fill=(170, 195, 230))
        d.text((14, h - 24), "CH1 HALL SIM", fill=(90, 120, 160))
        return img


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class GateEnvApp(object):
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("960x680")
        self.cfg = load_config(CONFIG_PATH, DEFAULT_CFG)
        self.db = EnvDB(os.path.join(BASE_DIR, self.cfg["db_file"]))
        self.cloud = create_client(self.cfg["mode"], self.cfg["cloud_url"],
                                   self.cfg["cloud_user"], self.cfg["cloud_pwd"])
        self.cam = CameraCtrl(self.cfg)
        self.snap_dir = os.path.join(BASE_DIR, self.cfg["snapshot_dir"])
        if not os.path.exists(self.snap_dir):
            os.makedirs(self.snap_dir)

        self.running = True
        self.last_save = 0
        self._tkimg = None
        self.door_open = False
        self._build_ui()
        self._close_door(notify=False)   # 启动默认关门
        threading.Thread(target=self._poll_env, daemon=True).start()

    # ---------------- UI ---------------- #
    def _build_ui(self):
        tk.Label(self.root, text="门闸环境监控系统",
                 font=("Microsoft YaHei", 15, "bold"),
                 bg="#00695C", fg="white", pady=8).pack(fill="x")

        # 环境数据
        env = tk.Frame(self.root, padx=8, pady=4)
        env.pack(fill="x")
        self.var_temp = tk.StringVar(value="温度: -- ℃")
        self.var_hum = tk.StringVar(value="湿度: -- %")
        self.var_co2 = tk.StringVar(value="CO2: -- ppm")
        self.var_noise = tk.StringVar(value="噪声: -- dB")
        for i, v in enumerate([self.var_temp, self.var_hum,
                               self.var_co2, self.var_noise]):
            tk.Label(env, textvariable=v, font=("Microsoft YaHei", 11),
                     width=18).grid(row=0, column=i, padx=6)

        # 门动画
        self.door_canvas = tk.Canvas(self.root, height=120, bg="#37474F",
                                     highlightthickness=0)
        self.door_canvas.pack(fill="x", padx=8, pady=4)
        self._door_l = self.door_canvas.create_rectangle(0, 10, 240, 110,
                                                          fill="#8D6E63", outline="")
        self._door_r = self.door_canvas.create_rectangle(240, 10, 480, 110,
                                                          fill="#8D6E63", outline="")
        self.var_door = tk.StringVar(value="闸门: 关门")
        tk.Label(self.root, textvariable=self.var_door,
                 font=("Microsoft YaHei", 11, "bold")).pack()

        # 门控按钮
        dr = tk.Frame(self.root)
        dr.pack(fill="x", padx=8, pady=4)
        tk.Button(dr, text="开门", bg="#2E7D32", fg="white", width=12,
                  command=self._open_door).pack(side="left", padx=4)
        tk.Button(dr, text="关门", bg="#C62828", fg="white", width=12,
                  command=self._close_door).pack(side="left", padx=4)

        # 监控画面
        self.video_label = tk.Label(self.root, bg="black", width=64, height=14)
        self.video_label.pack(fill="both", expand=True, padx=8, pady=4)
        if not HAVE_PIL:
            self.video_label.config(text="未安装 Pillow, 显示模拟占位\n(配置真实摄像头后自动取流)")

        # 云台方向
        ptz = tk.Frame(self.root)
        ptz.pack(pady=2)
        tk.Button(ptz, text="上", width=6, command=lambda: self._ptz("up")).grid(row=0, column=1)
        tk.Button(ptz, text="左", width=6, command=lambda: self._ptz("left")).grid(row=1, column=0)
        tk.Button(ptz, text="右", width=6, command=lambda: self._ptz("right")).grid(row=1, column=2)
        tk.Button(ptz, text="下", width=6, command=lambda: self._ptz("down")).grid(row=2, column=1)

        # 底部按钮
        bf = tk.Frame(self.root, padx=8, pady=6)
        bf.pack(fill="x")
        tk.Button(bf, text="截图", width=10, command=self._snapshot).pack(side="left", padx=4)
        tk.Button(bf, text="图片列表", width=10, command=self._open_images).pack(side="left", padx=4)
        tk.Button(bf, text="历史记录", width=10, command=self._open_history).pack(side="left", padx=4)

        self.root.after(500, self._refresh_video)

    # ---------------- 环境轮询 ---------------- #
    def _poll_env(self):
        tags = self.cfg["tags"]
        t = h = c = n = 0.0
        while self.running:
            try:
                t = self._read(tags["temp"], 26.0, 1.0)
                h = self._read(tags["hum"], 60.0, 2.0)
                c = self._read(tags["co2"], 520.0, 20.0)
                n = self._read(tags["noise"], 45.0, 3.0)
                self.root.after(0, lambda: self.var_temp.set("温度: %.1f ℃" % t))
                self.root.after(0, lambda: self.var_hum.set("湿度: %.1f %%" % h))
                self.root.after(0, lambda: self.var_co2.set("CO2: %.0f ppm" % c))
                self.root.after(0, lambda: self.var_noise.set("噪声: %.1f dB" % n))
                now = time.time()
                if now - self.last_save >= float(self.cfg.get("save_interval_sec", 5)):
                    self.db.insert(t, h, c, n)
                    self.last_save = now
            except Exception:
                pass
            time.sleep(1.0)

    def _read(self, tag, demo, amp):
        """读云传感器; demo 模式返回模拟值。"""
        try:
            v = self.cloud.list_all_tags().get(tag, {})
            val = v.get("value") if isinstance(v, dict) else None
            if val is not None:
                return float(val)
        except Exception:
            pass
        import random
        return round(demo + random.uniform(-amp, amp), 1)

    # ---------------- 门控制 ---------------- #
    def _open_door(self):
        self.door_open = True
        self._send_door(self.cfg["door"]["back_tag"], 1)
        self._send_door(self.cfg["door"]["putt_tag"], 0)
        self.var_door.set("闸门: 开门")
        self._animate_door(True)

    def _close_door(self, notify=True):
        self.door_open = False
        self._send_door(self.cfg["door"]["putt_tag"], 1)
        self._send_door(self.cfg["door"]["back_tag"], 0)
        if notify:
            self.var_door.set("闸门: 关门")
        else:
            self.var_door.set("闸门: 关门")
        self._animate_door(False)

    def _send_door(self, tag, val):
        def work():
            try:
                self.cloud.send_command(int(self.cfg.get("device_id", 1)), tag, val)
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _animate_door(self, open_):
        w = self.door_canvas.winfo_width() or 480
        half = w // 2
        # 关门: 两扇合拢到中线; 开门: 向两侧滑开
        if open_:
            self.door_canvas.coords(self._door_l, 0, 10, 40, 110)
            self.door_canvas.coords(self._door_r, w - 40, 10, w, 110)
        else:
            self.door_canvas.coords(self._door_l, 0, 10, half, 110)
            self.door_canvas.coords(self._door_r, half, 10, w, 110)

    # ---------------- 监控画面 ---------------- #
    def _refresh_video(self):
        if not self.running:
            return
        try:
            frame = self.cam.snapshot_frame()
            if frame is not None and HAVE_PIL:
                frame = frame.resize((self.video_label.winfo_width() or 480,
                                      self.video_label.winfo_height() or 200))
                self._tkimg = ImageTk.PhotoImage(frame)
                self.video_label.config(image=self._tkimg, width=0, height=0)
        except Exception:
            pass
        self.root.after(800, self._refresh_video)

    def _ptz(self, direction):
        threading.Thread(target=lambda: self.cam.ptz(direction), daemon=True).start()

    def _snapshot(self):
        try:
            frame = self.cam.snapshot_frame()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.snap_dir, "shot_%s.png" % ts)
            if frame is not None and HAVE_PIL:
                frame.save(path)
                messagebox.showinfo(APP_NAME, "已保存: %s" % path)
            else:
                with open(path + ".txt", "w", encoding="utf-8") as f:
                    f.write("截图占位 %s (未安装 Pillow)" % ts)
                messagebox.showinfo(APP_NAME, "已保存占位文件(未安装 Pillow)")
        except Exception as e:
            messagebox.showerror(APP_NAME, "截图失败: %s" % e)

    def _open_images(self):
        win = tk.Toplevel(self.root)
        win.title("图片列表")
        win.geometry("420x360")
        files = sorted([f for f in os.listdir(self.snap_dir)
                        if f.endswith((".png", ".jpg", ".jpeg"))], reverse=True)
        lb = tk.Listbox(win, font=("Consolas", 10))
        lb.pack(fill="both", expand=True, padx=8, pady=8)
        for f in files:
            lb.insert("end", f)
        tk.Button(win, text="返回首页", command=win.destroy).pack(pady=6)

    def _open_history(self):
        win = tk.Toplevel(self.root)
        win.title("历史记录")
        win.geometry("560x420")
        top = tk.Frame(win, padx=8, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="类型:").grid(row=0, column=0)
        cb = ttk.Combobox(top, values=["全部", "温度", "湿度", "CO2", "噪声"], width=8)
        cb.current(0); cb.grid(row=0, column=1, padx=4)
        tk.Label(top, text="起:").grid(row=0, column=2)
        e1 = tk.Entry(top, width=18); e1.grid(row=0, column=3, padx=4)
        tk.Label(top, text="止:").grid(row=0, column=4)
        e2 = tk.Entry(top, width=18); e2.grid(row=0, column=5, padx=4)

        cols = ("time", "value")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        tree.heading("time", text="记录时间")
        tree.heading("value", text="数值")
        tree.column("time", width=280); tree.column("value", width=160, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=4)

        def query():
            label = cb.get()
            type_ = {"温度": "temp", "湿度": "hum", "CO2": "co2",
                     "噪声": "noise"}.get(label, "")
            rows, col = self.db.query(type_, e1.get().strip(), e2.get().strip())
            tree.delete(*tree.get_children())
            for r in rows:
                if col:
                    tree.insert("", "end", values=(r[0], r[1]))
                else:
                    tree.insert("", "end",
                                values=(r[0], "%.1f/%.1f/%.0f/%.1f" % (r[1], r[2], r[3], r[4])))

        tk.Button(win, text="查询", command=query).pack(pady=2)
        tk.Button(win, text="返回首页", command=win.destroy).pack(pady=4)
        query()


def main():
    root = tk.Tk()
    GateEnvApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
