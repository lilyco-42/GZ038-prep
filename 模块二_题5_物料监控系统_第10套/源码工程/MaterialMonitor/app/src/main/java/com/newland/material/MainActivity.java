package com.newland.material;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.animation.Animation;
import android.view.animation.LinearInterpolator;
import android.view.animation.RotateAnimation;
import android.widget.ImageView;
import android.widget.TextView;

/**
 * 子任务2-5 物料监控系统。
 *
 * 业务规则:
 *  - 通过直流电机转速(m_speed)监测搅拌机, 界面实时显示转速, 并用旋转动画显示低/正常/高速搅拌效果。
 *  - 转速太快(>高速阈值): 右下角显示"转速太快", 报警灯 m_rotating_lamp 亮; 恢复正常则熄灭并隐藏提示。
 *  - 转速太慢(<低速阈值): 自动补料(电动推杆伸出 m_pushrod_putt), 补料中三色灯黄灯亮。
 *    完全伸出(限位开关 m_limit=1)后等待3秒 -> 推杆自动缩回(m_pushrod_back), 缩回过程黄灯保持亮;
 *    完全缩回(接近开关 m_near=1) -> 黄灯灭, 绿灯亮。
 *  - 补料过程中任意时刻按住微动开关(m_travelSwitch) -> 暂停补料, 红灯亮; 松开继续, 红灯灭。
 */
public class MainActivity extends Activity {

    /* 云服务设备标识(ApiTag), 与云服务系统录入保持一致 */
    private static final String TAG_SPEED   = "m_speed";          // 直流电机速度(搅拌机转速)
    private static final String TAG_ALARM   = "m_rotating_lamp";   // 报警灯(转速太快)
    private static final String TAG_PUTT_PUTT = "m_pushrod_putt"; // 电动推杆-前进(伸出补料)
    private static final String TAG_PUTT_BACK  = "m_pushrod_back"; // 电动推杆-后退(缩回)
    private static final String TAG_M_RED    = "m_multi_red";     // 多层指示灯-红
    private static final String TAG_M_YEL    = "m_multi_yellow";  // 多层指示灯-黄
    private static final String TAG_M_GRN    = "m_multi_green";   // 多层指示灯-绿
    private static final String TAG_EXTENDED = "m_limit";         // 限位开关=完全伸出
    private static final String TAG_RETRACTED= "m_near";          // 接近开关=完全缩回
    private static final String TAG_MICRO    = "m_travelSwitch";  // 微动开关(按住=暂停补料)

    /* 转速阈值(rpm), 按实际搅拌工艺调整 */
    private static final double SPEED_LOW  = 300.0;
    private static final double SPEED_HIGH = 1500.0;
    private static final long EXTEND_WAIT_MS = 3000; // 伸出到位后等待时间

    /* 云服务连接参数(按工位实际修改) */
    private static final String CLOUD_URL = "http://192.168.0.138";
    private static final String CLOUD_USER = "18912345600";
    private static final String CLOUD_PWD  = "123456";

    /* 补料状态机 */
    private static final int ST_IDLE = 0;
    private static final int ST_EXTEND = 1;   // 伸出补料中
    private static final int ST_WAIT = 2;     // 已伸出, 等待3秒缩回
    private static final int ST_RETRACT = 3;  // 缩回中
    private int state = ST_IDLE;
    private long waitStart = 0;
    private boolean paused = false;

    private CloudClient cloud;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private volatile boolean running = false;

    /* UI */
    private TextView tvSpeed, tvLevel, tvAlarm, tvState, tvR, tvY, tvG;
    private ImageView ivRotor;
    private RotateAnimation rotAnim;

    /* 上次下发值, 避免重复下发 */
    private int lastAlarm = -1, lastRed = -1, lastYel = -1, lastGrn = -1;
    private int lastPutt = -1, lastBack = -1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvSpeed = findViewById(R.id.tv_speed);
        tvLevel = findViewById(R.id.tv_level);
        tvAlarm = findViewById(R.id.tv_alarm);
        tvState = findViewById(R.id.tv_state);
        tvR = findViewById(R.id.tv_lamp_r);
        tvY = findViewById(R.id.tv_lamp_y);
        tvG = findViewById(R.id.tv_lamp_g);
        ivRotor = findViewById(R.id.iv_rotor);

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

    private void loop() {
        boolean ok = cloud.login(CLOUD_USER, CLOUD_PWD);
        if (ok) cloud.bindFirstDevice();
        while (running) {
            try { step(); } catch (Exception ignored) {}
            try { Thread.sleep(800); } catch (InterruptedException ignored) {}
        }
    }

    private void step() {
        Double sp = cloud.readSensor(TAG_SPEED);
        double speed = (sp == null) ? 0 : sp;
        Double ext = cloud.readSensor(TAG_EXTENDED);
        Double ret = cloud.readSensor(TAG_RETRACTED);
        Double mic = cloud.readSensor(TAG_MICRO);
        boolean extended = (ext != null && ext >= 1.0);
        boolean retracted = (ret != null && ret >= 1.0);
        boolean microHeld = (mic != null && mic >= 1.0);

        /* 转速太快报警(独立于补料流程) */
        boolean tooFast = speed > SPEED_HIGH;
        pushAlarm(tooFast ? 1 : 0);

        /* 微动开关暂停/恢复 */
        if (state == ST_EXTEND || state == ST_WAIT || state == ST_RETRACT) {
            paused = microHeld;
        } else {
            paused = false;
        }

        /* 暂停时红灯亮, 其他灯按补料流程维持但不推进 */
        if (paused) {
            pushTriLamp(1, 0, 0);
        }

        if (!paused) {
            switch (state) {
                case ST_IDLE:
                    pushTriLamp(0, 0, 1); // 待机绿灯
                    if (speed < SPEED_LOW) startExtend();
                    break;
                case ST_EXTEND:
                    pushTriLamp(0, 1, 0); // 黄灯
                    if (extended) { state = ST_WAIT; waitStart = System.currentTimeMillis(); }
                    break;
                case ST_WAIT:
                    pushTriLamp(0, 1, 0); // 黄灯保持
                    if (System.currentTimeMillis() - waitStart >= EXTEND_WAIT_MS) startRetract();
                    break;
                case ST_RETRACT:
                    pushTriLamp(0, 1, 0); // 缩回过程黄灯保持
                    if (retracted) finishRetract();
                    break;
            }
        }

        /* UI 刷新 */
        final double s = speed;
        final boolean fast = tooFast;
        final int st = state;
        handler.post(new Runnable() {
            @Override public void run() { refreshUi(s, fast, st); }
        });
    }

    private void startExtend() {
        pushPutt(1); pushBack(0);
        state = ST_EXTEND;
    }

    private void startRetract() {
        pushPutt(0); pushBack(1);
        state = ST_RETRACT;
    }

    private void finishRetract() {
        pushBack(0);
        pushTriLamp(0, 0, 1); // 黄灯灭, 绿灯亮
        state = ST_IDLE;
    }

    /* ---- 下发(去重) ---- */
    private void pushAlarm(int v) {
        if (v == lastAlarm) return;
        final int val = v;
        new Thread(new Runnable() { public void run() { cloud.sendCommand(TAG_ALARM, val); } }).start();
        lastAlarm = v;
    }

    private void pushTriLamp(int r, int y, int g) {
        if (r != lastRed) { final int v=r; new Thread(new Runnable(){public void run(){cloud.sendCommand(TAG_M_RED,v);}}).start(); lastRed=r; }
        if (y != lastYel) { final int v=y; new Thread(new Runnable(){public void run(){cloud.sendCommand(TAG_M_YEL,v);}}).start(); lastYel=y; }
        if (g != lastGrn) { final int v=g; new Thread(new Runnable(){public void run(){cloud.sendCommand(TAG_M_GRN,v);}}).start(); lastGrn=g; }
    }

    private void pushPutt(int v) {
        if (v == lastPutt) return;
        final int val = v;
        new Thread(new Runnable(){public void run(){cloud.sendCommand(TAG_PUTT_PUTT,val);}}).start();
        lastPutt = v;
    }

    private void pushBack(int v) {
        if (v == lastBack) return;
        final int val = v;
        new Thread(new Runnable(){public void run(){cloud.sendCommand(TAG_PUTT_BACK,val);}}).start();
        lastBack = v;
    }

    /* ---- UI ---- */
    private void refreshUi(double speed, boolean tooFast, int st) {
        tvSpeed.setText(String.format("当前转速: %.0f rpm", speed));
        String level;
        int levelColor;
        long dur;
        if (speed < SPEED_LOW) { level = "低速搅拌"; levelColor = Color.parseColor("#1565C0"); dur = 2500; }
        else if (speed > SPEED_HIGH) { level = "高速搅拌"; levelColor = Color.parseColor("#C62828"); dur = 400; }
        else { level = "正常搅拌"; levelColor = Color.parseColor("#2E7D32"); dur = 1200; }
        tvLevel.setText(level);
        tvLevel.setTextColor(levelColor);
        startRotate(dur);

        /* 右下角"转速太快"提示 */
        tvAlarm.setVisibility(tooFast ? TextView.VISIBLE : TextView.GONE);

        String stText;
        switch (st) {
            case ST_EXTEND: stText = paused ? "补料已暂停(微动开关)" : "补料中: 推杆伸出..."; break;
            case ST_WAIT:   stText = "补料中: 等待缩回..."; break;
            case ST_RETRACT:stText = paused ? "补料已暂停(微动开关)" : "补料中: 推杆缩回..."; break;
            default: stText = paused ? "补料已暂停(微动开关)" : "待机监控";
        }
        tvState.setText(stText);

        tvR.setBackgroundColor(lastRed==1 ? Color.RED : Color.DKGRAY);
        tvY.setBackgroundColor(lastYel==1 ? Color.YELLOW : Color.DKGRAY);
        tvG.setBackgroundColor(lastGrn==1 ? Color.GREEN : Color.DKGRAY);
    }

    private void startRotate(long durationMs) {
        if (rotAnim != null && rotAnim.getRepeatCount() == Animation.INFINITE) {
            // 持续旋转, 周期按转速更新
        }
        rotAnim = new RotateAnimation(0, 360,
                Animation.RELATIVE_TO_SELF, 0.5f, Animation.RELATIVE_TO_SELF, 0.5f);
        rotAnim.setDuration(durationMs);
        rotAnim.setRepeatCount(Animation.INFINITE);
        rotAnim.setInterpolator(new LinearInterpolator());
        ivRotor.startAnimation(rotAnim);
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
        /* 退出: 报警灯/三色灯/推杆全部复位 */
        new Thread(new Runnable() {
            public void run() {
                cloud.sendCommand(TAG_ALARM, 0);
                cloud.sendCommand(TAG_M_RED, 0);
                cloud.sendCommand(TAG_M_YEL, 0);
                cloud.sendCommand(TAG_M_GRN, 0);
                cloud.sendCommand(TAG_PUTT_PUTT, 0);
                cloud.sendCommand(TAG_PUTT_BACK, 0);
            }
        }).start();
    }
}
