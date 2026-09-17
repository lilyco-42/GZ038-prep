package com.cinema.newland.cinema;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;

/**
 * TCP 串口服务器客户端（2-4 智能电影院系统）。
 *
 * 程序通过 TCP 模式访问串口服务器，读取 CO2 传感器数据并控制
 * 风扇（ZigBee 继电器）、照明灯（ZigBee 继电器）、电动推杆（闸门）。
 *
 * 串口服务器默认：IP = 172.18.<工位号>.15，端口按对应串口配置
 * （Newland 串口服务器常见 8001/8002 等，现场以实际配置为准）。
 *
 * 说明：真实协议按串口服务器/设备 Modbus 或 ASCII 帧实现；
 *       本类把“连接-收发”封装好，业务层只调用 readCo2() / controlXxx()。
 */
public class TcpSerialClient {

    private static volatile TcpSerialClient instance;

    private String host = "172.18.0.15";
    private int port = 8001;

    private Socket socket;
    private OutputStream out;
    private InputStream in;
    private boolean connected = false;

    private TcpSerialClient() {
    }

    public static TcpSerialClient getInstance() {
        if (instance == null) {
            synchronized (TcpSerialClient.class) {
                if (instance == null) {
                    instance = new TcpSerialClient();
                }
            }
        }
        return instance;
    }

    public void setHost(String host, int port) {
        this.host = host;
        this.port = port;
    }

    /** 连接串口服务器（在子线程调用）。 */
    public synchronized boolean connect() {
        try {
            disconnect();
            socket = new Socket(host, port);
            socket.setSoTimeout(1000);
            out = socket.getOutputStream();
            in = socket.getInputStream();
            connected = true;
        } catch (Exception e) {
            connected = false;
        }
        return connected;
    }

    public boolean isConnected() {
        return connected && socket != null && socket.isConnected();
    }

    public synchronized void disconnect() {
        try {
            if (in != null) in.close();
            if (out != null) out.close();
            if (socket != null) socket.close();
        } catch (Exception ignored) {
        }
        in = null;
        out = null;
        socket = null;
        connected = false;
    }

    /** 发送一帧字节。 */
    private void sendFrame(byte[] frame) throws Exception {
        if (!isConnected()) connect();
        out.write(frame);
        out.flush();
    }

    /** 读取 CO2 传感器最新值（ppm）。读取失败返回 -1。 */
    public int readCo2() {
        try {
            // TODO: 按四输入/CO2 变送器 Modbus 协议组帧读取，例如：
            // byte[] req = {0x01, 0x04, 0x00, 0x00, 0x00, 0x01, <CRC_LO>, <CRC_HI>};
            // sendFrame(req);
            // byte[] resp = new byte[6];
            // int n = in.read(resp);
            // if (n >= 4) return ((resp[3] & 0xFF) | ((resp[2] & 0xFF) << 8));
            return -1;
        } catch (Exception e) {
            return -1;
        }
    }

    /** 控制 ZigBee 风扇（双联继电器一路）。on=true 开风扇。 */
    public void controlFan(boolean on) {
        try {
            // TODO: 按继电器 Modbus 写线圈帧下发：on -> 0xFF00，off -> 0x0000
            // byte[] req = buildWriteSingleCoil(RELAY_FAN_ADDR, on);
            // sendFrame(req);
        } catch (Exception ignored) {
        }
    }

    /** 控制 ZigBee 照明灯（双联继电器另一路）。 */
    public void controlLamp(boolean on) {
        try {
            // TODO: 同 controlFan，地址改为照明灯继电器
        } catch (Exception ignored) {
        }
    }

    /** 控制电动推杆（闸门）：open=true 伸开出闸，false=收回关闸。 */
    public void controlGate(boolean open) {
        try {
            // TODO: 电动推杆 m_pushrod_putt / m_pushrod_back 对应继电器
        } catch (Exception ignored) {
        }
    }
}
