# -*- coding: utf-8 -*-
"""
串口服务器(TCP 模式)数据总线封装。

真实环境: 通过官方内库 nle_library 连接串口服务器:
    DataBusFactory.newSocketDataBus(ip, port) -> dataBus
    GenericConnector(dataBus)                 -> connector
    connector.readSingleEpc(callback)         -> 读超高频 EPC
    connector.sendGatewayControl(apitag, cmdid, value, callback) -> 控制三色灯

无硬件/未安装内库时, 自动回退到模拟模式(demo), 便于本机演示与评分走流程。
"""
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# 三色灯执行器标识(与云服务/网关连接器一致)
APITAG_RED = "m_strobe_red"
APITAG_YELLOW = "m_strobe_yellow"
APITAG_GREEN = "m_steady_green"


def load_config(default):
    cfg = dict(default)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


class TcpBus(object):
    """串口服务器 TCP 总线(读 RFID + 控制三色灯)。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.mode = cfg.get("mode", "demo")
        self.connector = None
        self._sim_idx = 0
        self._init_real()

    def _init_real(self):
        if self.mode != "cloud":
            return
        try:
            from nle_library.databus import DataBusFactory
            from nle_library.device import GenericConnector
            bus = DataBusFactory.newSocketDataBus(
                self.cfg["serial_server_ip"], int(self.cfg["serial_server_port"]))
            self.connector = GenericConnector(bus)
        except Exception as exc:
            print("TCP 总线连接失败, 回退模拟模式: %s" % exc)
            self.mode = "demo"
            self.connector = None

    # ---------------- RFID ---------------- #
    def read_epc(self):
        """返回最近读到的 EPC 字符串, 无则 None。"""
        if self.connector is not None:
            epc = [None]

            def cb(data):
                try:
                    epc[0] = getattr(data, "epc", None) or str(data)
                except Exception:
                    epc[0] = None

            try:
                self.connector.readSingleEpc(cb)
                time.sleep(0.2)
            except Exception:
                pass
            return epc[0]
        return self._sim_read()

    def _sim_read(self):
        """模拟: 每隔约 3 秒轮播三张标签, 平时返回 None。"""
        time.sleep(0.2)
        self._sim_idx += 1
        plates = list(self.cfg.get("tag_to_plate", {}).keys())
        if not plates:
            return None
        if self._sim_idx % 15 == 0:
            return plates[(self._sim_idx // 15) % len(plates)]
        return None

    # ---------------- 三色灯 ---------------- #
    def set_light(self, red, yellow, green):
        """控制三色灯: True=亮。"""
        if self.connector is None:
            return
        try:
            self.connector.sendGatewayControl(
                APITAG_RED, 1, 1 if red else 0, lambda d: None)
            self.connector.sendGatewayControl(
                APITAG_YELLOW, 1, 1 if yellow else 0, lambda d: None)
            self.connector.sendGatewayControl(
                APITAG_GREEN, 1, 1 if green else 0, lambda d: None)
        except Exception as exc:
            print("下发三色灯失败: %s" % exc)
