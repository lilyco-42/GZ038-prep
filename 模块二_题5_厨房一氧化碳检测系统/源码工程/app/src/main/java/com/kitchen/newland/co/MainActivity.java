package com.kitchen.newland.co;

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
 * 厨房一氧化碳检测系统（2-5）主界面。
 *
 * 功能：
 *  - 从云服务系统读取 l_co 最新值，每 5s 刷新一次并显示。
 *  - 开启监控后：
 *      CO > 300  -> 开 ZigBee 风扇；CO <= 300 -> 关风扇（风扇转动动画）。
 *      CO > 800  -> 电动推杆伸出开窗；CO <= 800 -> 推杆收回关窗（窗户动画）。
 */
public class MainActivity extends Activity {

    /** 风扇阈值：>300 开风扇。 */
    private static final double FAN_THRESHOLD = 300.0;
    /** 开窗阈值：>800 推杆伸开出窗。 */
    private static final double WINDOW_THRESHOLD = 800.0;
    /** 云数据刷新周期：5s。 */
    private static final long POLL_INTERVAL = 5000;

    private TextView tvCo;
    private TextView tvFan;
    private TextView tvWindow;
    private ImageView ivFan;
    private ImageView ivWindow;
    private Button btnMonitor;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final CloudClient cloud = new CloudClient();

    private RotateAnimation fanSpin;
    private boolean monitoring = false;
    private boolean fanOn = false;
    private boolean windowOpen = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvCo = findViewById(R.id.tv_co_value);
        tvFan = findViewById(R.id.tv_fan_state);
        tvWindow = findViewById(R.id.tv_window_state);
        ivFan = findViewById(R.id.iv_fan);
        ivWindow = findViewById(R.id.iv_window);
        btnMonitor = findViewById(R.id.btn_monitor);

        // 现场云平台账号（C-5-2.txt 中记录）
        cloud.setAccount("http://192.168.0.138", "189123456XX", "******");

        fanSpin = new RotateAnimation(0f, 360f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f);
        fanSpin.setDuration(700);
        fanSpin.setRepeatCount(Animation.INFINITE);

        btnMonitor.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                toggleMonitor();
            }
        });
    }

    private void toggleMonitor() {
        monitoring = !monitoring;
        btnMonitor.setText(monitoring ? "停止监控" : "开启监控");
        Toast.makeText(this, monitoring ? "监控已开启" : "监控已停止",
                Toast.LENGTH_SHORT).show();
        if (monitoring) startPoll();
    }

    private void startPoll() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                // 先登录
                cloud.login();
                while (monitoring) {
                    final double co = cloud.readCo();
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            updateUi(co);
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

    private void updateUi(double co) {
        if (Double.isNaN(co)) {
            tvCo.setText("CO: 读取失败");
            return;
        }
        tvCo.setText("一氧化碳: " + (int) co + " ppm");

        // 风扇：>300 开，否则关
        boolean wantFan = co > FAN_THRESHOLD;
        if (wantFan != fanOn) {
            fanOn = wantFan;
            cloud.sendCommand(cloud.fanTag, fanOn ? 1 : 0);
            if (fanOn) {
                ivFan.startAnimation(fanSpin);
                tvFan.setText("风扇：开启");
            } else {
                ivFan.clearAnimation();
                tvFan.setText("风扇：关闭");
            }
        }

        // 窗户：>800 推杆伸开出窗，<=800 收回关窗
        boolean wantOpen = co > WINDOW_THRESHOLD;
        if (wantOpen != windowOpen) {
            windowOpen = wantOpen;
            if (windowOpen) {
                cloud.sendCommand(cloud.pushrodPut, 1);   // 伸开出窗
                tvWindow.setText("窗户：开启");
                ivWindow.setRotation(30);                 // 窗户开启动画示意
            } else {
                cloud.sendCommand(cloud.pushrodBack, 1);  // 收回关窗
                tvWindow.setText("窗户：关闭");
                ivWindow.setRotation(0);
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        monitoring = false;
        ivFan.clearAnimation();
    }
}
