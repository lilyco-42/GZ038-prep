package com.newland.pedestrian;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.ImageView;
import android.widget.TextView;

/**
 * 子任务2-4 行人闯红灯监控系统。
 *
 * 业务规则:
 *  - 行程开关(轮式)默认闭合 -> 界面红绿灯为绿灯; 摇臂断开 -> 红灯。
 *  - 红灯状态: 多层指示灯仅红灯亮, 其他灯灭;
 *  - 切到绿灯状态: 多层指示灯仅绿灯亮, 其他灯灭。
 *  - 绿灯状态: 显示"绿灯放行"图, 此时红外对射即使报警也不变化。
 *  - 红灯状态且红外对射不报警: 显示"红灯禁行"图, 报警灯灭。
 *  - 红灯状态且红外对射报警: 显示"行人闯红灯"图, 报警灯报警。
 *  - 退出 app 前, 红灯/绿灯/报警灯全部熄灭。
 */
public class MainActivity extends Activity {

    /* 云服务设备标识(ApiTag), 与云服务系统录入保持一致 */
    private static final String TAG_TRAVEL = "m_travelSwitch_singleWheel"; // 行程开关(轮式)
    private static final String TAG_LASER  = "m_laser";                    // 红外对射(激光对射)
    private static final String TAG_M_RED  = "m_multi_red";               // 多层指示灯-红
    private static final String TAG_M_GRN  = "m_multi_green";             // 多层指示灯-绿
    private static final String TAG_ALARM  = "m_rotating_lamp";           // 报警灯(转动指示灯)

    /* 云服务连接参数(按工位实际修改) */
    private static final String CLOUD_URL = "http://192.168.0.138";
    private static final String CLOUD_USER = "18912345600";
    private static final String CLOUD_PWD  = "123456";

    private CloudClient cloud;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean running = false;

    private TextView tvScene;       // 场景图区域(用色块+文字模拟三幅图)
    private TextView tvLight;       // 当前灯色提示
    private ImageView ivAlarm;      // 报警灯指示

    private int lastRed = -1, lastGreen = -1, lastAlarm = -1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvScene = findViewById(R.id.tv_scene);
        tvLight = findViewById(R.id.tv_light);
        ivAlarm = findViewById(R.id.iv_alarm);

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

    /** 后台轮询线程 */
    private void loop() {
        boolean ok = cloud.login(CLOUD_USER, CLOUD_PWD);
        if (ok) cloud.bindFirstDevice();
        while (running) {
            try {
                step();
            } catch (Exception e) {
                e.printStackTrace();
            }
            try { Thread.sleep(800); } catch (InterruptedException ignored) {}
        }
    }

    /** 采集一次并按业务规则决策 */
    private void step() {
        // 行程开关: 闭合(1)=绿灯, 断开(0)=红灯
        Double travel = cloud.readSensor(TAG_TRAVEL);
        // 红外对射: 1=报警
        Double laser = cloud.readSensor(TAG_LASER);

        boolean green = (travel != null && travel >= 1.0);
        boolean laserAlarm = (laser != null && laser >= 1.0);

        int red, greenLed, alarm;
        final String sceneText;
        final int sceneColor;

        if (green) {
            /* 绿灯放行: 仅绿灯亮, 红外报警也不变化 */
            red = 0; greenLed = 1; alarm = 0;
            sceneText = "绿灯放行";
            sceneColor = Color.parseColor("#2E7D32");
        } else {
            /* 红灯: 仅红灯亮 */
            red = 1; greenLed = 0;
            if (laserAlarm) {
                /* 红灯+红外报警 -> 闯红灯, 报警灯亮 */
                alarm = 1;
                sceneText = "行人闯红灯";
                sceneColor = Color.parseColor("#C62828");
            } else {
                /* 红灯+无报警 -> 红灯禁行, 报警灯灭 */
                alarm = 0;
                sceneText = "红灯禁行";
                sceneColor = Color.parseColor("#EF6C00");
            }
        }

        pushLamp(TAG_M_RED, red);
        pushLamp(TAG_M_GRN, greenLed);
        pushLamp(TAG_ALARM, alarm);

        final boolean greenNow = green;
        final boolean alarmNow = alarm == 1;
        handler.post(new Runnable() {
            @Override public void run() {
                tvScene.setText(sceneText);
                tvScene.setBackgroundColor(sceneColor);
                tvLight.setText(greenNow ? "当前: 绿灯" : "当前: 红灯");
                ivAlarm.setColorFilter(alarmNow ? Color.RED : Color.DKGRAY);
            }
        });
    }

    /** 下发执行器命令, 避免重复下发 */
    private void pushLamp(String tag, int value) {
        int last;
        if (tag.equals(TAG_M_RED)) last = lastRed;
        else if (tag.equals(TAG_M_GRN)) last = lastGreen;
        else last = lastAlarm;

        if (last != value) {
            cloud.sendCommand(tag, value);
            if (tag.equals(TAG_M_RED)) lastRed = value;
            else if (tag.equals(TAG_M_GRN)) lastGreen = value;
            else lastAlarm = value;
        }
    }

    /** 退出前: 红灯/绿灯/报警灯全部熄灭 */
    private void turnAllOff() {
        running = false;
        cloud.sendCommand(TAG_M_RED, 0);
        cloud.sendCommand(TAG_M_GRN, 0);
        cloud.sendCommand(TAG_ALARM, 0);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        turnAllOff();
    }
}
