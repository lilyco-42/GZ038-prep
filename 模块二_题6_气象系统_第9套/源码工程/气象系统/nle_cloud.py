# -*- coding: utf-8 -*-
"""
物联网云服务系统(NL-Cloud) RESTful 客户端 —— 标准库版(urllib)

说明:
  本机/赛场合规环境可能未安装 requests, 这里只用 Python 标准库 urllib,
  不引入任何第三方包。接口与赛项官方 nle_cloud.py 保持一致:
    1. POST {base}/users/login             登录, 返回 AccessToken
    2. GET  {base}/Devices                 查询设备
    3. GET  {base}/Devices/Datas?devIds=   批量取传感器最新值

另附 SimulatedCloudClient: 云服务不可达时返回模拟数据, 保证程序可运行验收。
"""

import json
import random
import urllib.request
import urllib.parse
from datetime import datetime

DEFAULT_TIMEOUT = 8


def _get(data, key):
    """大小写不敏感地取 JSON 字段。"""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == key.lower():
                return v
    return None


class CloudError(Exception):
    pass


class NLECloudClient(object):
    """真实云服务客户端(标准库 urllib)。"""

    def __init__(self, base_url, username=None, password=None):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.device_id = None
        self.last_error = ""

    def _http(self, method, path, payload=None, with_token=False):
        url = self.base_url + path
        data = None
        headers = {"Content-Type": "application/json"}
        if with_token and self.token:
            headers["AccessToken"] = self.token
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def login(self, username=None, password=None):
        if username:
            self.username = username
        if password:
            self.password = password
        try:
            data = self._http("POST", "/users/login",
                              {"Account": self.username, "Password": self.password,
                               "IsRememberMe": True})
        except Exception as exc:
            self.last_error = "登录请求失败: %s" % exc
            return False
        result = _get(data, "ResultObj")
        token = _get(result, "AccessToken") if isinstance(result, dict) else None
        if token:
            self.token = token
            return True
        self.last_error = str(_get(data, "Msg") or "登录失败")
        return False

    def bind_first_device(self):
        try:
            data = self._http("GET", "/Devices?PageSize=100&PageIndex=1", with_token=True)
            obj = _get(data, "ResultObj")
            arr = _get(obj, "PageSet") if isinstance(obj, dict) else None
            if not arr:
                arr = data.get("ResultObj")
            if arr:
                self.device_id = _get(arr[0], "DeviceID")
        except Exception as exc:
            self.last_error = "查询设备失败: %s" % exc
        return self.device_id

    def read_sensors(self, tags):
        """读取给定标识集合的最新值, 返回 {tag: float_value}。"""
        out = {}
        if self.device_id is None:
            self.bind_first_device()
        if self.device_id is None:
            return out
        try:
            data = self._http("GET", "/Devices/Datas?devIds=%s" % self.device_id,
                              with_token=True)
        except Exception as exc:
            self.last_error = "读传感器失败: %s" % exc
            return out
        arr = data.get("ResultObj")
        if arr is None and isinstance(data.get("ResultObj"), dict):
            arr = data["ResultObj"].get("Datas")
        for dev in (arr or []):
            for s in (dev.get("Datas") or [dev]):
                tag = _get(s, "ApiTag")
                if tag in tags:
                    val = _get(s, "Value")
                    try:
                        out[tag] = float(val)
                    except (TypeError, ValueError):
                        pass
        return out


class SimulatedCloudClient(object):
    """模拟客户端: 云服务不可达时生成稳定波动的演示数据。"""

    _PROFILE = {
        "m_temp": (26.0, 1.5),
        "m_hum": (58.0, 3.0),
        "m_light": (320.0, 40.0),
        "m_co2": (480.0, 40.0),
        "m_noise": (45.0, 3.0),
    }

    def __init__(self, *a, **kw):
        self._state = {}

    def login(self, *a, **kw):
        return True

    def bind_first_device(self):
        return 1

    def read_sensors(self, tags):
        out = {}
        for tag in tags:
            center, amp = self._PROFILE.get(tag, (50.0, 5.0))
            v = self._state.get(tag, center)
            v = max(center - amp * 2, min(center + amp * 2, v + random.uniform(-amp, amp) * 0.5))
            self._state[tag] = v
            out[tag] = round(v, 1)
        return out


def create_client(mode, base_url, username, password):
    """mode: 'cloud' 真实云服务 / 'demo' 模拟。"""
    if mode == "demo":
        return SimulatedCloudClient()
    return NLECloudClient(base_url, username, password)


def load_config(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(default)
