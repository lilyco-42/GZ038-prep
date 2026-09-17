# -*- coding: utf-8 -*-
"""
监控管理系统 - 社区视频监控系统
竞赛任务 2-6
运行环境: Python 3.11 + tkinter + requests + Pillow
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import queue
import time
import json
import os
import io
import random
import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ========== 全局配置 ==========
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "camera": {
        "ip": "192.168.1.100",
        "port": 80,
        "user": "admin",
        "pass": "admin123",
        "snapshot_url": "http://{ip}:{port}/snapshot.jpg",
        "stream_url": "http://{ip}:{port}/videostream.cgi?user={user}&pwd={pass}",
        "ptz_url": "http://{ip}:{port}/ptz_control.cgi?cmd={dir}&user={user}&pwd={pass}"
    },
    "interval_ms": 80,
    "timeout": 3
}

# 主题色 - 对齐参考图 image12
COLOR_BG_DARK = "#3a3a3a"
COLOR_BG_MID = "#2b2b2b"
COLOR_BG_LIGHT = "#1e90ff"
COLOR_ACCENT = "#1e90ff"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_DIM = "#aaaaaa"
COLOR_GREEN = "#27ae60"
COLOR_RED = "#e74c3c"
COLOR_YELLOW = "#f1c40f"
COLOR_BORDER = "#444444"
COLOR_CANVAS_BG = "#2a2a2a"
COLOR_BTN_DIR = "#1a1a1a"
COLOR_BTN_DIR_HOVER = "#333333"

# 兼容 Pillow 缩放常量
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.LANCZOS


def load_config():
    """加载配置文件，不存在则使用默认值并创建"""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
        except Exception:
            pass
    return cfg


def build_url(template, cam, direction=None):
    """根据 URL 模板与摄像头配置构建完整地址"""
    if not template:
        return ""
    url = template
    url = url.replace("{ip}", str(cam.get("ip", "")))
    url = url.replace("{port}", str(cam.get("port", 80)))
    url = url.replace("{user}", str(cam.get("user", "")))
    url = url.replace("{pass}", str(cam.get("pass", "")))
    if direction:
        url = url.replace("{dir}", direction)
    return url


# ========== 模拟画面生成器 ==========
class SimulatedFrameGenerator:
    """生成模拟监控画面：深色背景 + 网格线 + 红点REC + 时间戳"""

    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.frame_count = 0

    def generate(self):
        """生成一帧模拟画面"""
        img = Image.new("RGB", (self.width, self.height), (5, 14, 26))
        draw = ImageDraw.Draw(img)
        self.frame_count += 1

        # 细网格线
        for x in range(0, self.width, 40):
            draw.line([(x, 0), (x, self.height)], fill=(15, 35, 60), width=1)
        for y in range(0, self.height, 40):
            draw.line([(0, y), (self.width, y)], fill=(15, 35, 60), width=1)

        # 粗网格线
        for x in range(0, self.width, 160):
            draw.line([(x, 0), (x, self.height)], fill=(25, 50, 85), width=1)
        for y in range(0, self.height, 160):
            draw.line([(0, y), (self.width, y)], fill=(25, 50, 85), width=1)

        # 中心十字准线
        cx, cy = self.width // 2, self.height // 2
        cross_color = (40, 70, 110)
        draw.line([(cx - 60, cy), (cx + 60, cy)], fill=cross_color, width=1)
        draw.line([(cx, cy - 60), (cx, cy + 60)], fill=cross_color, width=1)
        draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40],
                     outline=cross_color, width=1)
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6],
                     outline=cross_color, width=2)

        # 加载字体
        font_rec = font_time = font_info = font_center = None
        for path in ("msyh.ttc", "arial.ttf"):
            try:
                font_rec = ImageFont.truetype(path, 18)
                break
            except Exception:
                continue
        for path in ("consola.ttf", "arial.ttf"):
            try:
                font_time = ImageFont.truetype(path, 13)
                break
            except Exception:
                continue
        for path in ("msyh.ttc", "arial.ttf"):
            try:
                font_info = ImageFont.truetype(path, 11)
                break
            except Exception:
                continue
        for path in ("msyh.ttc", "arial.ttf"):
            try:
                font_center = ImageFont.truetype(path, 16)
                break
            except Exception:
                continue
        if font_rec is None:
            font_rec = ImageFont.load_default()
        if font_time is None:
            font_time = ImageFont.load_default()
        if font_info is None:
            font_info = ImageFont.load_default()
        if font_center is None:
            font_center = ImageFont.load_default()

        # REC 红点（闪烁）
        if self.frame_count % 40 < 28:
            draw.ellipse([20, 18, 38, 36], fill=(220, 40, 40))
            draw.text((44, 16), "REC", fill=(230, 60, 60), font=font_rec)

        # 右上角时间戳
        now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        draw.text((self.width - 200, 18), now_str,
                  fill=(170, 195, 230), font=font_time)

        # 左下角通道信息
        draw.text((18, self.height - 36), "CH1 - SIMULATION MODE",
                  fill=(100, 130, 170), font=font_info)

        # 右下角帧计数
        draw.text((self.width - 150, self.height - 36),
                  "Frame %06d" % self.frame_count,
                  fill=(90, 120, 160), font=font_info)

        # 中心提示（前若干帧渐变显示）
        if self.frame_count < 200:
            alpha = max(0, round(255 * (200 - self.frame_count) / 200.0))
            txt = "监控连接失败 - 使用模拟画面"
            bbox = draw.textbbox((0, 0), txt, font=font_center)
            tw = bbox[2] - bbox[0]
            tx = (self.width - tw) // 2
            ty = self.height // 2 + 80
            col = (alpha, alpha, alpha)
            draw.text((tx, ty), txt, fill=col, font=font_center)

        # 动态噪点
        random.seed(int(time.time() * 10) + self.frame_count)
        for _ in range(10):
            rx = random.randint(0, self.width - 3)
            ry = random.randint(0, self.height - 3)
            rc = random.randint(8, 28)
            draw.rectangle([rx, ry, rx + 2, ry + 2], fill=(rc, rc, rc + 6))

        return img


# ========== 主应用 ==========
class MonitorApp:
    """监控管理系统主界面"""

    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.cam = self.config["camera"]

        # 线程与状态变量
        self.is_monitoring = False
        self.stop_event = threading.Event()
        self.capture_thread = None
        self.sim_thread = None
        self.sim_mode = False
        self.stream_resp = None
        self.failed_count = 0
        self.max_fail = 5

        self.frame_queue = queue.Queue(maxsize=3)
        self.status_queue = queue.Queue()
        self.sim_generator = SimulatedFrameGenerator(640, 480)

        # 界面尺寸
        self.win_w = 900
        self.win_h = 620
        self.cam_w = 600
        self.cam_h = 450

        self._setup_window()
        self._setup_styles()
        self._build_ui()
        self._update_clock()
        self._show_default_frame()
        self._poll_queues()

    # ---------- 窗口设置 ----------
    def _setup_window(self):
        self.root.title("监控管理系统")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry("%dx%d+%d+%d" % (self.win_w, self.win_h,
                                            (sw - self.win_w) // 2,
                                            (sh - self.win_h) // 2))
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG_DARK)

    def _setup_styles(self):
        self.font_title = tkfont.Font(family="Microsoft YaHei", size=15, weight="bold")
        self.font_label = tkfont.Font(family="Microsoft YaHei", size=10)
        self.font_btn = tkfont.Font(family="Microsoft YaHei", size=11, weight="bold")
        self.font_dir = tkfont.Font(family="Microsoft YaHei", size=12, weight="bold")
        self.font_status = tkfont.Font(family="Consolas", size=9)
        self.font_clock = tkfont.Font(family="Consolas", size=10)

    # ---------- 构建界面 ----------
    def _build_ui(self):
        # 顶部标题栏
        top_bar = tk.Frame(self.root, bg=COLOR_BG_LIGHT, height=46, bd=0)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.pack_propagate(False)

        tk.Frame(top_bar, bg=COLOR_ACCENT, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(top_bar, text="  视频监控",
                 bg=COLOR_BG_LIGHT, fg=COLOR_TEXT,
                 font=self.font_title).pack(side=tk.LEFT, padx=8)
        tk.Label(top_bar, text="",
                 bg=COLOR_BG_LIGHT, fg=COLOR_TEXT_DIM,
                 font=("Consolas", 9)).pack(side=tk.LEFT, padx=12)

        # 主体区
        main_area = tk.Frame(self.root, bg=COLOR_BG_DARK)
        main_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

        # 左：摄像头播放区
        left_frame = tk.Frame(main_area, bg=COLOR_BG_DARK)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cam_header = tk.Frame(left_frame, bg=COLOR_BG_MID, height=26)
        cam_header.pack(fill=tk.X)
        cam_header.pack_propagate(False)
        tk.Label(cam_header, text="  摄像头播放区",
                 bg=COLOR_BG_MID, fg=COLOR_TEXT_DIM,
                 font=self.font_label).pack(side=tk.LEFT, padx=6)
        self.status_indicator = tk.Label(cam_header, text="● 未连接",
                                          bg=COLOR_BG_MID, fg=COLOR_RED,
                                          font=self.font_status)
        self.status_indicator.pack(side=tk.RIGHT, padx=10)

        canvas_frame = tk.Frame(left_frame, bg=COLOR_BORDER, bd=1)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.canvas = tk.Canvas(canvas_frame, bg=COLOR_CANVAS_BG,
                                highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 右：控制面板
        right_frame = tk.Frame(main_area, bg=COLOR_BG_MID, width=230)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        right_frame.pack_propagate(False)

        # --- 圆形方向盘 ---
        tk.Label(right_frame, text="云台控制",
                 bg=COLOR_BG_MID, fg=COLOR_TEXT_DIM,
                 font=self.font_label).pack(pady=(12, 4))

        wheel_size = 180
        self.wheel_canvas = tk.Canvas(right_frame, width=wheel_size, height=wheel_size,
                                       bg=COLOR_BG_MID, highlightthickness=0, bd=0)
        self.wheel_canvas.pack(pady=(4, 8))
        # 外圆(黑色)
        cx = cy = wheel_size // 2
        r_outer = 85
        self.wheel_canvas.create_oval(cx-r_outer, cy-r_outer, cx+r_outer, cy+r_outer,
                                      fill="#111111", outline="#333333", width=3)
        # 内圆
        self.wheel_canvas.create_oval(cx-20, cy-20, cx+20, cy+20,
                                      fill="#222222", outline="#555555", width=2)
        # 4 个方向箭头 (三角形)
        arrow_r = 45
        # 上 ▲
        self.wheel_canvas.create_polygon(
            cx, cy-arrow_r-12, cx-12, cy-arrow_r+10, cx+12, cy-arrow_r+10,
            fill="#e74c3c", outline="")
        # 下 ▼
        self.wheel_canvas.create_polygon(
            cx, cy+arrow_r+12, cx-12, cy+arrow_r-10, cx+12, cy+arrow_r-10,
            fill="#e74c3c", outline="")
        # 左 ◀
        self.wheel_canvas.create_polygon(
            cx-arrow_r-12, cy, cx-arrow_r+10, cy-12, cx-arrow_r+10, cy+12,
            fill="#e74c3c", outline="")
        # 右 ▶
        self.wheel_canvas.create_polygon(
            cx+arrow_r+12, cy, cx+arrow_r-10, cy-12, cx+arrow_r-10, cy+12,
            fill="#e74c3c", outline="")
        # 点击方向盘
        self.wheel_center = (cx, cy)
        self.wheel_canvas.bind("<Button-1>", self._on_wheel_click)

        self.dir_buttons = {}  # 兼容旧引用(不再用矩形按钮)

        self.ptz_label = tk.Label(right_frame, text="",
                                   bg=COLOR_BG_MID, fg=COLOR_YELLOW,
                                   font=self.font_status)
        self.ptz_label.pack(pady=(0, 8))

        # --- 打开/停止监控 按钮(方向盘下方) ---
        btn_box = tk.Frame(right_frame, bg=COLOR_BG_MID)
        btn_box.pack(pady=(4, 8))

        self.btn_start = tk.Button(btn_box, text="打开监控", font=self.font_btn,
                                    bg="#5a5a5a", fg=COLOR_TEXT,
                                    activebackground="#707070",
                                    activeforeground=COLOR_TEXT,
                                    relief=tk.FLAT, bd=0, width=10, height=1,
                                    command=self._start_monitor)
        self.btn_start.pack(pady=4)

        self.btn_stop = tk.Button(btn_box, text="停止监控", font=self.font_btn,
                                   bg="#5a5a5a", fg=COLOR_TEXT,
                                   activebackground="#707070",
                                   activeforeground=COLOR_TEXT,
                                   relief=tk.FLAT, bd=0, width=10, height=1,
                                   state=tk.DISABLED,
                                   command=self._stop_monitor)
        self.btn_stop.pack(pady=4)

        # 底部控制栏(只留状态+时钟)
        bottom_bar = tk.Frame(self.root, bg=COLOR_BG_LIGHT, height=40, bd=0)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        bottom_bar.pack_propagate(False)

        self.status_text = tk.Label(bottom_bar, text="就绪",
                                     bg=COLOR_BG_LIGHT, fg=COLOR_TEXT_DIM,
                                     font=self.font_status)
        self.status_text.pack(side=tk.LEFT, padx=12, pady=8)

        self.clock_label = tk.Label(bottom_bar, text="",
                                     bg=COLOR_BG_LIGHT, fg=COLOR_TEXT_DIM,
                                     font=self.font_clock)
        self.clock_label.pack(side=tk.RIGHT, padx=16, pady=8)

    def _on_wheel_click(self, event):
        """圆形方向盘点击: 根据点击位置相对圆心判断方向。"""
        cx, cy = self.wheel_center
        dx = event.x - cx
        dy = event.y - cy
        if abs(dx) < 15 and abs(dy) < 15:
            return  # 中心点不触发
        # 比较 |dx| 和 |dy| 决定方向
        if abs(dx) > abs(dy):
            cmd = "right" if dx > 0 else "left"
        else:
            cmd = "down" if dy > 0 else "up"
        self._send_ptz(cmd, {"up": "上", "down": "下",
                              "left": "左", "right": "右"}[cmd])

    # ---------- 时钟 ----------
    def _update_clock(self):
        self.clock_label.config(text=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self._update_clock)

    # ---------- 默认画面 ----------
    def _show_default_frame(self):
        """绘制“摄像头未开启”默认静态画面"""
        w, h = self.cam_w, self.cam_h
        img = Image.new("RGB", (w, h), (5, 14, 26))
        draw = ImageDraw.Draw(img)

        for x in range(0, w, 40):
            draw.line([(x, 0), (x, h)], fill=(12, 25, 45), width=1)
        for y in range(0, h, 40):
            draw.line([(0, y), (w, y)], fill=(12, 25, 45), width=1)

        cx, cy = w // 2, h // 2 - 20
        # 摄像头图标
        draw.rounded_rectangle([cx - 32, cy - 18, cx + 32, cy + 18],
                               radius=6, outline=(60, 95, 135), width=2)
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12],
                     outline=(85, 125, 175), width=2)
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5],
                     outline=(105, 150, 200), width=1)

        font_main = font_sub = None
        for path in ("msyh.ttc", "arial.ttf"):
            try:
                font_main = ImageFont.truetype(path, 16)
                break
            except Exception:
                continue
        for path in ("msyh.ttc", "arial.ttf"):
            try:
                font_sub = ImageFont.truetype(path, 10)
                break
            except Exception:
                continue
        if font_main is None:
            font_main = ImageFont.load_default()
        if font_sub is None:
            font_sub = ImageFont.load_default()

        text = "摄像头未开启"
        bbox = draw.textbbox((0, 0), text, font=font_main)
        draw.text(((w - (bbox[2] - bbox[0])) // 2, cy + 42), text,
                  fill=(100, 140, 190), font=font_main)

        sub = "请点击「打开监控」按钮开始"
        bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
        draw.text(((w - (bbox2[2] - bbox2[0])) // 2, cy + 70), sub,
                  fill=(65, 95, 135), font=font_sub)

        self._display_pil_image(img)

    def _display_pil_image(self, pil_img):
        """将 PIL 图片缩放后绘制到 Canvas"""
        try:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw < 10:
                cw = self.cam_w
            if ch < 10:
                ch = self.cam_h
            img = pil_img.copy()
            img.thumbnail((cw, ch), RESAMPLE)
            self._tk_img = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(cw // 2, ch // 2,
                                     image=self._tk_img, anchor=tk.CENTER)
        except Exception:
            pass

    # ---------- 开始监控 ----------
    def _start_monitor(self):
        if self.is_monitoring:
            return
        self.is_monitoring = True
        self.stop_event.clear()
        self.sim_mode = False
        self.failed_count = 0
        self.stream_resp = None

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_indicator.config(text="● 连接中...", fg=COLOR_YELLOW)
        self.status_text.config(text="正在连接摄像头...")
        self.status_text.config(text="模式：连接中", fg=COLOR_YELLOW)

        self.capture_thread = threading.Thread(target=self._capture_loop,
                                               daemon=True)
        self.capture_thread.start()

    # ---------- 停止监控 ----------
    def _stop_monitor(self):
        if not self.is_monitoring:
            return
        self.is_monitoring = False
        self.stop_event.set()

        if self.stream_resp:
            try:
                self.stream_resp.close()
            except Exception:
                pass
            self.stream_resp = None

        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)

        # 清空队列
        try:
            while True:
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass

        self.sim_mode = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_indicator.config(text="● 已断开", fg=COLOR_RED)
        self.status_text.config(text="监控已停止")
        self.status_text.config(text="模式：待机", fg=COLOR_TEXT_DIM)
        self.ptz_label.config(text="")

        self._show_default_frame()

    # ---------- 后台抓帧（独立线程） ----------
    def _emit(self, msg_type, *args):
        """线程安全地向主线程投递消息"""
        try:
            self.status_queue.put_nowait((msg_type,) + args)
        except Exception:
            pass

    def _capture_loop(self):
        """先尝试 MJPEG 流，失败或中断后降级为快照轮询"""
        self._try_mjpeg_stream()

        # 快照轮询模式
        while not self.stop_event.is_set():
            frame = self._grab_snapshot()
            if frame is not None:
                self.failed_count = 0
                if self.sim_mode:
                    self.sim_mode = False
                    self._emit("recover")
                try:
                    self.frame_queue.put(frame, timeout=0.1)
                except queue.Full:
                    pass
            else:
                self.failed_count += 1
                if self.failed_count >= self.max_fail and not self.sim_mode:
                    self.sim_mode = True
                    self._emit("sim")

            self.stop_event.wait(timeout=max(0.02,
                                  self.config.get("interval_ms", 80) / 1000.0))

    def _try_mjpeg_stream(self):
        """尝试建立 MJPEG 流连接并持续读帧"""
        if self.stop_event.is_set():
            return
        try:
            url = build_url(self.cam.get("stream_url",
                            "http://{ip}:{port}/videostream.cgi?user={user}&pwd={pass}"),
                            self.cam)
            resp = requests.get(url, stream=True,
                                timeout=self.config.get("timeout", 3))
            if resp.status_code != 200:
                resp.close()
                return
            self.stream_resp = resp
            self._emit("indicator", "● 已连接", COLOR_GREEN)
            self._emit("mode", "模式：MJPEG 流", COLOR_GREEN)
            self._emit("status", "MJPEG 视频流已连接")
            self._read_mjpeg_stream()
        except Exception:
            pass

    def _read_mjpeg_stream(self):
        """在 MJPEG 流中解析 JPEG 帧"""
        resp = self.stream_resp
        buf = b""
        try:
            while not self.stop_event.is_set():
                chunk = resp.raw.read(4096)
                if not chunk:
                    break
                buf += chunk
                buf_len = len(buf)
                # 逐帧解析：FFD8...FFD9
                while True:
                    start = buf.find(b"\xff\xd8")
                    if start == -1:
                        buf = buf[-1:]
                        break
                    end = buf.find(b"\xff\xd9", start + 2)
                    if end == -1:
                        if len(buf) > 200000:
                            buf = buf[start:]
                        break
                    jpeg = buf[start:end + 2]
                    buf = buf[end + 2:]
                    if len(jpeg) > 100:
                        try:
                            img = Image.open(io.BytesIO(jpeg)).convert("RGB")
                            self.failed_count = 0
                            if self.sim_mode:
                                self.sim_mode = False
                                self._emit("recover")
                            try:
                                self.frame_queue.put(img, timeout=0.1)
                            except queue.Full:
                                pass
                        except Exception:
                            continue
        except Exception:
            pass
        finally:
            if self.stream_resp:
                try:
                    self.stream_resp.close()
                except Exception:
                    pass
                self.stream_resp = None

    def _grab_snapshot(self):
        """抓取一帧快照图片"""
        try:
            url = build_url(self.cam.get("snapshot_url",
                            "http://{ip}:{port}/snapshot.jpg"), self.cam)
            resp = requests.get(url, timeout=self.config.get("timeout", 3))
            if resp.status_code == 200 and len(resp.content) > 100:
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except Exception:
            pass
        return None

    # ---------- 模拟模式 ----------
    def _enter_sim_mode(self):
        """进入模拟画面模式（主线程调用）"""
        self.sim_generator = SimulatedFrameGenerator(self.cam_w, self.cam_h)
        self.status_text.config(text="模式：模拟画面", fg=COLOR_YELLOW)
        self.status_text.config(text="监控连接失败，使用模拟画面")
        if self.sim_thread is None or not self.sim_thread.is_alive():
            self.sim_thread = threading.Thread(target=self._sim_loop, daemon=True)
            self.sim_thread.start()

    def _sim_loop(self):
        """模拟帧生成线程"""
        while not self.stop_event.is_set() and self.sim_mode:
            img = self.sim_generator.generate()
            try:
                self.frame_queue.put(img, timeout=0.1)
            except queue.Full:
                pass
            self.stop_event.wait(timeout=0.1)

    # ---------- 主线程轮询 ----------
    def _poll_queues(self):
        """主线程定时轮询帧队列与状态队列"""
        # 状态消息
        try:
            while True:
                msg = self.status_queue.get_nowait()
                mtype = msg[0]
                if mtype == "sim":
                    self._enter_sim_mode()
                elif mtype == "recover":
                    self.sim_mode = False
                    self.status_indicator.config(text="● 已连接", fg=COLOR_GREEN)
                    self.status_text.config(text="模式：实时监控", fg=COLOR_GREEN)
                    self.status_text.config(text="摄像头已恢复连接")
                elif mtype == "indicator":
                    self.status_indicator.config(text=msg[1], fg=msg[2])
                elif mtype == "mode":
                    self.status_text.config(text=msg[1], fg=msg[2])
                elif mtype == "status":
                    self.status_text.config(text=msg[1])
                elif mtype == "ptz":
                    self.ptz_label.config(text=msg[1])
                    self.status_text.config(text=msg[1])
                    self.root.after(2500,
                                    lambda: self.ptz_label.config(text=""))
        except queue.Empty:
            pass

        # 帧消息
        if self.is_monitoring:
            frame = None
            try:
                while True:
                    frame = self.frame_queue.get_nowait()
            except queue.Empty:
                pass
            if frame is not None:
                self._display_pil_image(frame)

        self.root.after(50, self._poll_queues)

    # ---------- 云台控制 ----------
    def _send_ptz(self, direction, name):
        """发送云台（PTZ）方向控制指令"""
        if not self.is_monitoring:
            return
        self.ptz_label.config(text="发送云台指令：%s" % name)
        self.status_text.config(text="发送云台指令：%s" % name)
        self.root.after(2500, lambda: self.ptz_label.config(text=""))

        def _do_ptz():
            ok = False
            try:
                url = build_url(self.cam.get("ptz_url",
                                "http://{ip}:{port}/ptz_control.cgi?cmd={dir}&user={user}&pwd={pass}"),
                                self.cam, direction=direction)
                resp = requests.get(url, timeout=min(3,
                                    self.config.get("timeout", 3)))
                ok = resp.status_code == 200
            except Exception:
                ok = False

            if self.sim_mode:
                # 模拟模式下只提示“已发送”，不显示失败
                self._emit("ptz", "已发送云台指令：%s" % name)
            elif ok:
                self._emit("ptz", "已发送云台指令：%s" % name)
            else:
                self._emit("ptz", "云台控制失败")

        threading.Thread(target=_do_ptz, daemon=True).start()

    # ---------- 关闭 ----------
    def on_close(self):
        """窗口关闭：停止线程并退出"""
        self.stop_event.set()
        self.is_monitoring = False
        if self.stream_resp:
            try:
                self.stream_resp.close()
            except Exception:
                pass
        self.root.destroy()


# ========== 启动入口 ==========
def main():
    root = tk.Tk()
    app = MonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
