package com.newland.roomtemp;

import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import java.util.Locale;

/**
 * 子任务2-5 室内温湿度
 *   读取工位温湿度传感器, 实时显示温度/湿度。
 *   赛题样式要求:
 *     "温度""湿度" 标签用白色字体;
 *     温度监测值色号 #01A7FF;
 *     湿度监测值色号 #35D529。
 *
 * 传感器标识: 温度 m_temp, 湿度 m_hum。
 */
public class MainActivity extends AppCompatActivity {

    private static final String TAG_TEMP = "m_temp";
    private static final String TAG_HUM  = "m_hum";
    private static final long POLL_MS = 2000;   /* 2 秒刷新一次 */

    /** 赛题指定色号 */
    private static final int COLOR_LABEL = Color.WHITE;          /* 温度/湿度标签: 白 */
    private static final int COLOR_TEMP  = Color.parseColor("#01A7FF");
    private static final int COLOR_HUM   = Color.parseColor("#35D529");

    private TextView tvTempLabel, tvHumLabel;
    private TextView tvTempVal, tvHumVal;
    private TextView tvStatus;

    private CloudClient cloud;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private boolean running = false;

    private final Runnable pollTask = new Runnable() {
        @Override
        public void run() {
            if (!running) return;
            refreshOnce();
            ui.postDelayed(this, POLL_MS);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        if (getSupportActionBar() != null) getSupportActionBar().setTitle("室内温湿度");

        tvTempLabel = findViewById(R.id.tv_temp_label);
        tvHumLabel  = findViewById(R.id.tv_hum_label);
        tvTempVal   = findViewById(R.id.tv_temp_val);
        tvHumVal    = findViewById(R.id.tv_hum_val);
        tvStatus    = findViewById(R.id.tv_status);

        /* 赛题色号: 标签白色; 温度值 #01A7FF; 湿度值 #35D529 */
        tvTempLabel.setTextColor(COLOR_LABEL);
        tvHumLabel.setTextColor(COLOR_LABEL);
        tvTempVal.setTextColor(COLOR_TEMP);
        tvHumVal.setTextColor(COLOR_HUM);

        startCloud();
    }

    /** 登录云服务并启动轮询 */
    private void startCloud() {
        tvStatus.setText("正在连接云服务...");
        new Thread(() -> {
            cloud = new CloudClient("http://192.168.0.138");
            // 工位账号密码在实际部署时可在此或配置中填入; 这里尝试登录。
            boolean ok = cloud.login("18900000000", "");
            if (ok) ok = cloud.bindFirstDevice() >= 0;
            final boolean res = ok;
            ui.post(() -> {
                if (res) {
                    tvStatus.setText("实时监测中");
                    running = true;
                    ui.post(pollTask);
                } else {
                    tvStatus.setText("未连接云服务, 显示演示数据");
                    running = true;
                    ui.post(demoTask);   // 无云服务时演示数据兜底
                }
            });
        }).start();
    }

    private void refreshOnce() {
        if (cloud == null) return;
        Double t = cloud.readSensor(TAG_TEMP);
        Double h = cloud.readSensor(TAG_HUM);
        ui.post(() -> {
            if (t != null && !t.isNaN()) tvTempVal.setText(String.format(Locale.CHINA, "%.1f ℃", t));
            if (h != null && !h.isNaN()) tvHumVal.setText(String.format(Locale.CHINA, "%.1f %%", h));
        });
    }

    /** 无云服务时的演示数据(便于界面验收) */
    private final Runnable demoTask = new Runnable() {
        double t = 25.0, h = 55.0;
        @Override
        public void run() {
            if (!running) return;
            t += (Math.random() - 0.5);
            h += (Math.random() - 0.5) * 2;
            tvTempVal.setText(String.format(Locale.CHINA, "%.1f ℃", t));
            tvHumVal.setText(String.format(Locale.CHINA, "%.1f %%", h));
            ui.postDelayed(this, POLL_MS);
        }
    };

    @Override
    protected void onDestroy() {
        super.onDestroy();
        running = false;
        ui.removeCallbacks(pollTask);
        ui.removeCallbacks(demoTask);
    }
}
