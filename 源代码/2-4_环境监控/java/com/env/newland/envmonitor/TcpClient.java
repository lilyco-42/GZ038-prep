package com.env.newland.envmonitor;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.Locale;
import java.util.Random;

/**
 * TCP 工具类。
 *  - connectData(host, port)：建立数据连接，后台线程按行读取服务器推送数据，回传给回调。
 *  - sendCmd(host, port, data)：短连接发送控制指令。
 *  - 断线后每 3 秒自动重连。
 *  - DemoSensorThread：无真实数据时生成模拟传感器数据。
 */
public class TcpClient {

    public interface OnLineListener {
        void onLine(String line);
    }

    public interface OnStatusListener {
        void onStatusChanged(boolean connected);
    }

    public interface OnLogListener {
        void onLog(String msg);
    }

    private static final int CONNECT_TIMEOUT_MS = 4000;
    private static final int RECONNECT_DELAY_MS = 3000;

    private OnLineListener lineListener;
    private OnStatusListener statusListener;
    private OnLogListener logListener;

    private String dataHost = "192.168.1.100";
    private int dataPort = 8899;

    private volatile boolean running;
    private volatile boolean connected;
    private Thread dataThread;
    private Thread demoThread;

    public TcpClient() {
    }

    public void setDataAddress(String host, int port) {
        if (host != null && host.length() > 0) {
            dataHost = host;
        }
        dataPort = port;
    }

    public void setLineListener(OnLineListener l) {
        lineListener = l;
    }

    public void setStatusListener(OnStatusListener l) {
        statusListener = l;
    }

    public void setLogListener(OnLogListener l) {
        logListener = l;
    }

    /** 启动数据监听线程（内含断线自动重连）。 */
    public void start() {
        if (running) {
            return;
        }
        running = true;
        connected = false;
        dataThread = new Thread(new Runnable() {
            @Override
            public void run() {
                dataLoop();
            }
        }, "envmonitor-data");
        dataThread.setDaemon(true);
        dataThread.start();
    }

    public void stop() {
        running = false;
        connected = false;
        notifyStatus(false);
        if (dataThread != null) {
            try {
                dataThread.join(1500);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            dataThread = null;
        }
    }

    public boolean isConnected() {
        return connected;
    }

    private void dataLoop() {
        while (running) {
            Socket socket = null;
            try {
                socket = new Socket();
                socket.connect(new InetSocketAddress(dataHost, dataPort), CONNECT_TIMEOUT_MS);
                connected = true;
                notifyStatus(true);
                log("已连接到数据服务器 " + dataHost + ":" + dataPort);
                InputStream in = socket.getInputStream();
                BufferedReader reader = new BufferedReader(new InputStreamReader(in, "UTF-8"));
                String line;
                while (running && (line = reader.readLine()) != null) {
                    if (lineListener != null) {
                        try {
                            lineListener.onLine(line);
                        } catch (Exception ignore) {
                        }
                    }
                }
                if (running) {
                    log("数据服务器连接已断开");
                }
            } catch (Exception e) {
                if (running) {
                    log("连接失败: " + e.getMessage());
                }
            } finally {
                connected = false;
                notifyStatus(false);
                if (socket != null) {
                    try {
                        socket.close();
                    } catch (Exception ignore) {
                    }
                }
            }
            if (running) {
                log(RECONNECT_DELAY_MS / 1000 + " 秒后尝试重新连接...");
                sleepQuietly(RECONNECT_DELAY_MS);
            }
        }
    }

    /** 短连接发送一条控制指令（独立线程执行，可主线程直接调用）。 */
    public void sendCmd(final String host, final int port, final String data) {
        if (data == null || data.length() == 0) {
            return;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                Socket socket = null;
                try {
                    socket = new Socket();
                    socket.connect(new InetSocketAddress(host, port), 3000);
                    OutputStream os = socket.getOutputStream();
                    os.write(data.getBytes("UTF-8"));
                    os.flush();
                    log("控制指令已发送: " + data.trim());
                } catch (Exception e) {
                    log("控制指令发送失败: " + e.getMessage());
                } finally {
                    if (socket != null) {
                        try {
                            socket.close();
                        } catch (Exception ignore) {
                        }
                    }
                }
            }
        }, "envmonitor-control").start();
    }

    /** 启动演示数据线程（模拟数据经同一回调送达）。 */
    public void startDemo() {
        if (demoThread != null) {
            return;
        }
        final DemoSensorThread[] holder = new DemoSensorThread[1];
        holder[0] = new DemoSensorThread(new OnLineListener() {
            @Override
            public void onLine(String line) {
                if (lineListener != null) {
                    try {
                        lineListener.onLine(line);
                    } catch (Exception ignore) {
                    }
                }
            }
        }, new Runnable() {
            @Override
            public void run() {
                synchronized (TcpClient.this) {
                    if (demoThread == holder[0]) {
                        demoThread = null;
                    }
                }
            }
        });
        demoThread = holder[0];
        holder[0].setDaemon(true);
        holder[0].start();
    }

    public void stopDemo() {
        final Thread t = demoThread;
        demoThread = null;
        if (t != null && t instanceof DemoSensorThread) {
            DemoSensorThread d = (DemoSensorThread) t;
            d.shutdown();
            try {
                d.join(500);
            } catch (InterruptedException ignore) {
                Thread.currentThread().interrupt();
            }
        }
    }

    public boolean isDemoRunning() {
        return demoThread != null;
    }

    private void sleepQuietly(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private void notifyStatus(final boolean ok) {
        if (statusListener != null) {
            try {
                statusListener.onStatusChanged(ok);
            } catch (Exception ignore) {
            }
        }
    }

    private void log(final String msg) {
        if (logListener != null) {
            try {
                logListener.onLog(msg);
            } catch (Exception ignore) {
            }
        }
    }

    /**
     * 演示传感器线程：每 2 秒生成一行模拟数据。
     * 温湿度 18~35、光照 20~180、人体 0/1 随机切换。
     */
    public static class DemoSensorThread extends Thread {

        private final OnLineListener out;
        private final Runnable onStop;
        private final Random random = new Random();
        private double temp = 26.0;
        private double hum = 55.0;
        private double light = 100.0;
        private int human = 0;
        private volatile boolean alive = true;

        public DemoSensorThread(OnLineListener out, Runnable onStop) {
            this.out = out;
            this.onStop = onStop;
        }

        @Override
        public void run() {
            while (alive) {
                temp += (random.nextDouble() - 0.5) * 0.6;
                hum += (random.nextDouble() - 0.5) * 1.4;
                light += (random.nextDouble() - 0.5) * 10;
                if (temp < 18) temp = 18;
                if (temp > 35) temp = 35;
                if (hum < 30) hum = 30;
                if (hum > 80) hum = 80;
                if (light < 20) light = 20;
                if (light > 180) light = 180;
                if (random.nextInt(8) == 0) {
                    human = 1 - human;
                }
                String line = String.format(Locale.CHINA,
                        "T:%.1f H:%.1f L:%.1f P:%d", temp, hum, light, human);
                if (out != null) {
                    try {
                        out.onLine(line);
                    } catch (Exception ignore) {
                    }
                }
                try {
                    Thread.sleep(2000);
                } catch (InterruptedException e) {
                    alive = false;
                    break;
                }
            }
            if (onStop != null) {
                try {
                    onStop.run();
                } catch (Exception ignore) {
                }
            }
        }

        public void shutdown() {
            alive = false;
            interrupt();
        }
    }
}