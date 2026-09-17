package com.cinema.newland.cinema;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.animation.Animation;
import android.view.animation.RotateAnimation;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

/**
 * 影院主界面（2-4 智能电影院系统）。
 *
 * 功能：
 *  - 实时监测 CO2（四输入传感器）：定时经 TCP 串口服务器读取。
 *  - CO2 大于给定阈值时：打开风扇并播放风扇转动动画；低于阈值关闭风扇与动画。
 *  - 点击“照明灯”按钮：打开/关闭照明灯（ZigBee 继电器）。
 *  - 所有设备读写均通过 TCP 模式访问串口服务器。
 */
public class MainActivity extends Activity {

    /** CO2 风扇阈值(ppm)，现场可调。 */
    private static final int CO2_FAN_THRESHOLD = 1000;
    /** CO2 轮询周期(ms)。 */
    private static final long POLL_INTERVAL = 2000;

    private TextView tvCo2;
    private TextView tvFanState;
    private ImageView ivFan;
    private Button btnLamp;
    private Button btnBack;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private RotateAnimation fanRotate;
    private boolean fanOn = false;
    private boolean lampOn = false;
    private boolean monitoring = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvCo2 = findViewById(R.id.tv_co2);
        tvFanState = findViewById(R.id.tv_fan_state);
        ivFan = findViewById(R.id.iv_fan);
        btnLamp = findViewById(R.id.btn_lamp);
        btnBack = findViewById(R.id.btn_back);

        TcpSerialClient.getInstance().setHost("172.18.0.15", 8001);

        // 风扇转动动画（匀速无限旋转）
        fanRotate = new RotateAnimation(0f, 360f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f);
        fanRotate.setDuration(800);
        fanRotate.setRepeatCount(Animation.INFINITE);

        btnLamp.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                toggleLamp();
            }
        });

        btnBack.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });

        startCo2Poll();
    }

    /** 子线程周期性读 CO2，结果回主线程更新 UI。 */
    private void startCo2Poll() {
        monitoring = true;
        new Thread(new Runnable() {
            @Override
            public void run() {
                while (monitoring) {
                    final int co2 = TcpSerialClient.getInstance().readCo2();
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            updateCo2(co2);
                        }
                    });
                    try {
                        Thread.sleep(POLL_INTERVAL);
                    } catch (InterruptedException e) {
                        break;
                    }
                }
            }
        }).start();
    }

    private void updateCo2(int co2) {
        if (co2 < 0) {
            tvCo2.setText("CO2: 读取失败");
            return;
        }
        tvCo2.setText("CO2: " + co2 + " ppm");

        // CO2 超阈值开风扇+动画，否则关
        boolean shouldFan = co2 > CO2_FAN_THRESHOLD;
        if (shouldFan && !fanOn) {
            fanOn = true;
            TcpSerialClient.getInstance().controlFan(true);
            ivFan.startAnimation(fanRotate);
            tvFanState.setText("风扇：开启（CO2 偏高）");
        } else if (!shouldFan && fanOn) {
            fanOn = false;
            TcpSerialClient.getInstance().controlFan(false);
            ivFan.clearAnimation();
            tvFanState.setText("风扇：关闭");
        }
    }

    /** 点击照明灯：开/关切换。 */
    private void toggleLamp() {
        lampOn = !lampOn;
        TcpSerialClient.getInstance().controlLamp(lampOn);
        btnLamp.setText(lampOn ? "照明灯：开" : "照明灯：关");
        Toast.makeText(this, lampOn ? "照明灯已打开" : "照明灯已关闭",
                Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        monitoring = false;
        ivFan.clearAnimation();
        TcpSerialClient.getInstance().disconnect();
    }
}
