# -*- coding: utf-8 -*-
"""
物联网云服务系统(NL-Cloud / nlecloud) RESTful API 客户端模块。

接口说明(基于新大陆物联网云平台 RESTful API):
    1. POST  {base}/users/login             用户登录, 返回 AccessToken
    2. GET   {base}/Devices                 模糊查询用户设备
    3. GET   {base}/Devices/Datas?devIds=.. 批量查询设备内全部传感器最新数据
    4. GET   {base}/Devices/{id}            查询单个设备(含传感器最新值)
    5. POST  {base}/Devices/{id}/Cmds       向执行器下发命令

本实现仅依赖 Python 标准库(urllib), 不依赖 requests, 便于在离线/无第三方包环境运行;
另附 SimulatedCloudClient 模拟客户端, 用于无硬件时演示与评分走流程。
"""

import json
import os
import random
import time
from datetime import datetime
from urllib import request as _urlrequest
from urllib.parse import urlencode

DEFAULT_TIMEOUT = 10


def _get(data, key):
    """大小写不敏感地获取 JSON 字段值。"""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == key.lower():
                return v
    return None


class CloudError(Exception):
    """云服务调用异常。"""


def _http(method, url, body=None, token=None, timeout=DEFAULT_TIMEOUT):
    """最小化 HTTP 调用(标准库), 返回解析后的 JSON。"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["AccessToken"] = token
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = _urlrequest.Request(url, data=data, headers=headers, method=method)
    resp = _urlrequest.urlopen(req, timeout=timeout)
    raw = resp.read().decode("utf-8")
    return json.loads(raw)


class NLECloudClient(object):
    """物联网云服务系统客户端。"""

    def __init__(self, base_url, username=None, password=None):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.user = None
        self.last_error = ""

    # ---------------- 登录 ---------------- #
    def login(self, username=None, password=None):
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password
        if not self.base_url:
            self.last_error = "未配置云服务地址"
            return False, self.last_error
        if not self.username or not self.password:
            self.last_error = "用户名或密码不能为空"
            return False, self.last_error
        try:
            data = _http("POST", self.base_url + "/users/login",
                         {"Account": self.username, "Password": self.password,
                          "IsRememberMe": True})
        except Exception as exc:
            self.last_error = "登录请求失败: %s" % exc
            return False, self.last_error
        result = _get(data, "ResultObj")
        token = _get(result, "AccessToken") if isinstance(result, dict) else None
        if token:
            self.token = token
            self.user = result
            return True, "登录成功"
        msg = _get(data, "Msg") or "登录失败"
        self.last_error = str(msg)
        return False, self.last_error

    # ---------------- 设备 ---------------- #
    def query_devices(self, project_keyword=None, keyword=None, page_size=100):
        self._ensure_token()
        params = {"PageSize": page_size, "PageIndex": 1}
        if project_keyword:
            params["ProjectKeyWord"] = project_keyword
        if keyword:
            params["Keyword"] = keyword
        url = self.base_url + "/Devices?" + urlencode(params)
        data = _http("GET", url, token=self.token)
        result = _get(data, "ResultObj") or {}
        page_set = _get(result, "PageSet") or []
        if not page_set and isinstance(result, list):
            page_set = result
        return page_set or []

    def get_device(self, device_id):
        self._ensure_token()
        url = "%s/Devices/%s" % (self.base_url, device_id)
        data = _http("GET", url, token=self.token)
        return _get(data, "ResultObj") or {}

    # ---------------- 传感数据 ---------------- #
    def get_latest_datas(self, dev_ids):
        self._ensure_token()
        ids = []
        for d in dev_ids:
            if d not in ids:
                ids.append(d)
        if not ids:
            return []
        url = self.base_url + "/Devices/Datas?" + urlencode(
            {"devIds": ",".join(str(i) for i in ids)})
        data = _http("GET", url, token=self.token)
        result = _get(data, "ResultObj") or []
        return result or []

    def list_all_tags(self, device_ids=None):
        ids = []
        if device_ids:
            ids = [int(x) for x in device_ids]
        else:
            devices = self.query_devices()
            if devices:
                ids = [_get(d, "DeviceID") for d in devices
                       if _get(d, "DeviceID") is not None]
        out = {}
        for dev in self.get_latest_datas(ids) or []:
            for sensor in _get(dev, "Datas") or []:
                tag = _get(sensor, "ApiTag")
                if tag:
                    out[tag] = {"value": _get(sensor, "Value"),
                                "time": _get(sensor, "RecordTime")}
        return out

    # ---------------- 命令下发 ---------------- #
    def send_command(self, device_id, api_tag, value):
        self._ensure_token()
        url = "%s/Devices/%s/Cmds" % (self.base_url, device_id)
        payload = {"apikey": self.token, "apitag": api_tag, "value": value}
        try:
            data = _http("POST", url, payload, token=self.token)
        except Exception as exc:
            return False, "指令发送失败: %s" % exc
        status_code = _get(data, "StatusCode")
        if status_code in (1, 2):
            return True, _get(data, "Msg") or "发送成功"
        return False, _get(data, "Msg") or "发送失败"

    def _ensure_token(self):
        if not self.token:
            raise CloudError("尚未登录, 请先调用 login()")


class SimulatedCloudClient(object):
    """模拟测试客户端(无硬件时使用)。"""

    def __init__(self, base_url="", username="demo", password="demo"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = "SIMULATED-TOKEN"
        self.last_error = ""

    def login(self, username=None, password=None):
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password
        return True, "模拟模式登录成功(演示数据)"

    def query_devices(self):
        return [{"DeviceID": 1, "Name": "模拟网关"}]

    def send_command(self, device_id, api_tag, value):
        return True, "模拟下发成功"


def save_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_config(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(default)


def normalize_number(value, default=None):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return default


def create_client(mode, base_url, username, password):
    """按模式创建客户端。mode: cloud(真实云服务) / demo(模拟测试)。"""
    if mode == "demo":
        return SimulatedCloudClient(base_url, username, password)
    return NLECloudClient(base_url, username, password)
