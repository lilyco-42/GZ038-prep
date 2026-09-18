package com.newland.location;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;

import java.util.Locale;

/**
 * 子任务2-5 位置定位系统（GZ038 第8套）。
 *
 * 业务规则:
 *  - 云服务"智能环境云 / 位置监测"场景下, NS(LoRa) 每 5s 上报经纬度的度/分/秒:
 *      Longitude1(度) Longitude2(分) Longitude3(秒)
 *      Latitude1(度)  Latitude2(分)  Latitude3(秒)
 *  - App 每 5s 读取一次最新值, 按 1度=60分, 1分=60秒 换算成十进制度:
 *      十进制度 = 度 + 分/60 + 秒/3600
 *  - 经度、纬度均保留 6 位小数显示。
 *  - 云南省范围: 经度 97.527278 ~ 106.196958, 纬度 21.142312 ~ 29.225286。
 *      在范围内 -> 报警灯灭, 显示"云南省";
 *      不在范围 -> 报警灯亮, 显示"区域外"。
 */
public class MainActivity extends Activity {

    /* 云服务传感器标识(ApiTag), 与"位置监测"场景录入一致 */
    private static final String TAG_LON_D = "Longitude1";
    private static final String TAG_LON_M = "Longitude2";
    private static final String TAG_LON_S = "Longitude3";
    private static final String TAG_LAT_D = "Latitude1";
    private static final String TAG_LAT_M = "Latitude2";
    private static final String TAG_LAT_S = "Latitude3";

    /* 报警灯执行器标识(超范围点亮, 现场按实际执行器修改) */
    private static final String TAG_ALARM = "m_strobe_red";

    /* 云服务连接参数(按工位实际修改) */
    private static final String CLOUD_URL  = "http://192.168.0.138";
    private static final String CLOUD_USER = "18912345600";
    private static final String CLOUD_PWD  = "123456";

    /* 云南省经纬度范围 */
    private static final double YN_LON_MIN = 97.527278;
    private static final double YN_LON_MAX = 106.196958;
    private static final double YN_LAT_MIN = 21.142312;
    private static final double YN_LAT_MAX = 29.225286;

    private CloudClient cloud;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private volatile boolean running = false;
    private int lastAlarm = -1;

    private TextView tvLon;
    private TextView tvLat;
    private TextView tvRegion;
    private TextView tvAlarm;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvLon    = findViewById(R.id.tv_lon);
        tvLat    = findViewById(R.id.tv_lat);
        tvRegion = findViewById(R.id.tv_region);
        tvAlarm  = findViewById(R.id.tv_alarm);

        cloud = new CloudClient(CLOUD_URL);
    }

    @Override
    protected void onResume() {
        super.onResume();
        running = true;
        new Thread(new Runnable() {
            @Override public void run() { loop(); }
        }).start();
    }

    /** 后台轮询线程, 5s 一次 */
    private void loop() {
        boolean ok = cloud.login(CLOUD_USER, CLOUD_PWD);
        if (ok) cloud.bindFirstDevice();
        while (running) {
            try {
                step();
            } catch (Exception e) {
                e.printStackTrace();
            }
            try { Thread.sleep(5000); } catch (InterruptedException ignored) {}
        }
    }

    /** 采集一次并换算、判断 */
    private void step() {
        Double lonD = cloud.readSensor(TAG_LON_D);
        Double lonM = cloud.readSensor(TAG_LON_M);
        Double lonS = cloud.readSensor(TAG_LON_S);
        Double latD = cloud.readSensor(TAG_LAT_D);
        Double latM = cloud.readSensor(TAG_LAT_M);
        Double latS = cloud.readSensor(TAG_LAT_S);

        /* 任一缺失则等待下一周期 */
        if (lonD == null || lonM == null || lonS == null
                || latD == null || latM == null || latS == null) {
            return;
        }

        /* 度分秒 -> 十进制度 */
        final double lon = dmsToDecimal(lonD, lonM, lonS);
        final double lat = dmsToDecimal(latD, latM, latS);

        /* 范围判断 */
        final boolean inYunnan = (lon >= YN_LON_MIN && lon <= YN_LON_MAX
                && lat >= YN_LAT_MIN && lat <= YN_LAT_MAX);

        /* 报警灯: 区域外点亮, 否则熄灭(避免重复下发) */
        final int alarm = inYunnan ? 0 : 1;
        if (alarm != lastAlarm) {
            cloud.sendCommand(TAG_ALARM, alarm);
            lastAlarm = alarm;
        }

        final String region = inYunnan ? "云南省" : "区域外";
        handler.post(new Runnable() {
            @Override public void run() {
                /* 经度、纬度均保留 6 位小数 */
                tvLon.setText(String.format(Locale.getDefault(),
                        "经度: %.6f°", lon));
                tvLat.setText(String.format(Locale.getDefault(),
                        "纬度: %.6f°", lat));
                tvRegion.setText("当前位置: " + region);
                tvRegion.setTextColor(inYunnan
                        ? Color.parseColor("#2E7D32")
                        : Color.parseColor("#C62828"));
                tvAlarm.setText(alarm == 1 ? "报警灯: 亮" : "报警灯: 灭");
            }
        });
    }

    /** 度分秒 -> 十进制度: 度 + 分/60 + 秒/3600 */
    private double dmsToDecimal(double deg, double min, double sec) {
        return deg + min / 60.0 + sec / 3600.0;
    }

    @Override
    protected void onPause() {
        super.onPause();
        running = false;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        running = false;
        /* 退出前熄灭报警灯 */
        cloud.sendCommand(TAG_ALARM, 0);
    }
}
