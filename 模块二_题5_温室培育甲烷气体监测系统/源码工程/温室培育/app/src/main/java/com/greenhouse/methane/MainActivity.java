package com.greenhouse.methane;

import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.support.v7.app.AppCompatActivity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.animation.Animation;
import android.view.animation.LinearInterpolator;
import android.view.animation.RotateAnimation;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

/**
 * 子任务2-5 温室培育甲烷气体监测系统 主界面。
 *
 * 界面结构（单 Activity + 登录遮罩 + 主界面）：
 *   - 图1 登录页：模态遮罩覆盖在主界面之上；右上角设置按钮 -> 图3 设置弹窗；
 *     点击“登录”用云服务用户名密码验证，成功后关闭遮罩显示图2 主界面。
 *   - 图2 主界面：显示甲烷实时值与阈值；风扇图片在超标时旋转(动画)、
 *     低于阈值时停止；支持 自动/手动 两种模式控制风扇；可注销退出，
 *     再次进入主界面需要重新登录。
 *
 * 说明：由原 Kotlin 版 MainActivity.kt 直译而来，业务逻辑保持一致。
 */
public class MainActivity extends AppCompatActivity {

    private static final String PREFS = "greenhouse_prefs";
    private static final long POLL_MS = 3000L;         // 甲烷数据刷新周期

    private SharedPreferences prefs;
    private CloudApi cloud;
    private final Handler handler = new Handler(Looper.getMainLooper());

    // 主界面控件
    private TextView tvMethane;
    private TextView tvThreshold;
    private TextView tvMode;
    private ImageView ivFan;
    private Button btnMode;
    private Button btnFanOn;
    private Button btnFanOff;
    private Button btnLogout;

    // 登录遮罩控件
    private LinearLayout loginMask;
    private EditText etUser;
    private EditText etPass;
    private Button btnLogin;
    private Button btnOpenSettings;

    // 运行状态
    private boolean logged = false;
    private boolean autoMode = true;          // 默认自动
    private boolean fanOn = false;
    private RotateAnimation fanRotAnim;
    private Runnable pollRunnable;

    // 配置项（SharedPreferences 持久化）
    private String serverUrl = "http://192.168.0.138";
    private double threshold = 25.0;
    private String sensorTag = "m_Methane1";
    private String fanTag = "z_fan";          // 风扇执行器标识，按工位实际配置
    private int devId = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        loadConfig();
        cloud = new CloudApi(serverUrl);

        bindViews();
        // 恢复上次保存的用户名（对应 Kotlin 版 loadConfig 中 etUser?.setText 的运行时机）
        etUser.setText(prefs.getString("username", ""));
        setupListeners();
        buildFanAnimation();
        showLogin();                       // 启动即显示登录遮罩（图1）
    }

    private void bindViews() {
        tvMethane = (TextView) findViewById(R.id.tv_methane);
        tvThreshold = (TextView) findViewById(R.id.tv_threshold);
        tvMode = (TextView) findViewById(R.id.tv_mode);
        ivFan = (ImageView) findViewById(R.id.iv_fan);
        btnMode = (Button) findViewById(R.id.btn_mode);
        btnFanOn = (Button) findViewById(R.id.btn_fan_on);
        btnFanOff = (Button) findViewById(R.id.btn_fan_off);
        btnLogout = (Button) findViewById(R.id.btn_logout);

        loginMask = (LinearLayout) findViewById(R.id.login_mask);
        etUser = (EditText) findViewById(R.id.et_user);
        etPass = (EditText) findViewById(R.id.et_pass);
        btnLogin = (Button) findViewById(R.id.btn_login);
        btnOpenSettings = (Button) findViewById(R.id.btn_open_settings);
    }

    private void setupListeners() {
        btnLogin.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { doLogin(); }
        });
        btnOpenSettings.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { showSettingsDialog(); }
        });
        btnLogout.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { doLogout(); }
        });
        btnMode.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { toggleMode(); }
        });
        btnFanOn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { manualFan(true); }
        });
        btnFanOff.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { manualFan(false); }
        });
    }

    // ---------------- 配置读写 ---------------- //

    private void loadConfig() {
        serverUrl = prefs.getString("server_url", serverUrl);
        String th = prefs.getString("threshold", String.valueOf(threshold));
        threshold = parseDouble(th, 25.0);
        sensorTag = prefs.getString("sensor_tag", sensorTag);
        fanTag = prefs.getString("fan_tag", fanTag);
    }

    private static double parseDouble(String s, double def) {
        try {
            return Double.parseDouble(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    private void saveConfig() {
        prefs.edit()
                .putString("server_url", serverUrl)
                .putString("threshold", String.valueOf(threshold))
                .putString("sensor_tag", sensorTag)
                .putString("fan_tag", fanTag)
                .apply();
        tvThreshold.setText("甲烷报警阈值: " + threshold + " %");
    }

    // ---------------- 登录 / 注销 ---------------- //

    private void showLogin() {
        logged = false;
        stopPoll();
        loginMask.setVisibility(View.VISIBLE);
        loginMask.setAlpha(0.96f);            // 背景遮罩
    }

    private void doLogin() {
        String user = etUser.getText().toString().trim();
        String pass = etPass.getText().toString().trim();
        if (user.isEmpty() || pass.isEmpty()) {
            Toast.makeText(this, "请输入用户名和密码", Toast.LENGTH_SHORT).show();
            return;
        }
        btnLogin.setEnabled(false);
        Toast.makeText(this, "正在登录云服务系统...", Toast.LENGTH_SHORT).show();
        final String fUser = user;
        final String fPass = pass;
        new Thread(new Runnable() {
            @Override public void run() {
                final boolean ok = cloud.login(fUser, fPass);
                handler.post(new Runnable() {
                    @Override public void run() {
                        btnLogin.setEnabled(true);
                        if (ok) {
                            prefs.edit().putString("username", fUser).apply();
                            logged = true;
                            loginMask.setVisibility(View.GONE);
                            Toast.makeText(MainActivity.this, "登录成功", Toast.LENGTH_SHORT).show();
                            startPoll();
                        } else {
                            Toast.makeText(MainActivity.this, "登录失败，请检查账号密码", Toast.LENGTH_LONG).show();
                        }
                    }
                });
            }
        }).start();
    }

    private void doLogout() {
        stopPoll();
        setFan(false);
        logged = false;
        cloud = new CloudApi(serverUrl);
        showLogin();
        Toast.makeText(this, "已注销，请重新登录", Toast.LENGTH_SHORT).show();
    }

    // ---------------- 设置弹窗（图3） ---------------- //

    private void showSettingsDialog() {
        View v = LayoutInflater.from(this).inflate(R.layout.dialog_settings, null);
        final EditText etServer = (EditText) v.findViewById(R.id.et_server);
        final EditText etThreshold = (EditText) v.findViewById(R.id.et_threshold);
        final EditText etSensor = (EditText) v.findViewById(R.id.et_sensor_tag);
        final EditText etFan = (EditText) v.findViewById(R.id.et_fan_tag);

        etServer.setText(serverUrl);
        etThreshold.setText(String.valueOf(threshold));
        etSensor.setText(sensorTag);
        etFan.setText(fanTag);

        AlertDialog.Builder b = new AlertDialog.Builder(this);
        b.setTitle("设置");
        b.setView(v);
        b.setPositiveButton("保存", new android.content.DialogInterface.OnClickListener() {
            @Override public void onClick(android.content.DialogInterface dialog, int which) {
                serverUrl = etServer.getText().toString().trim();
                double th = parseDouble(etThreshold.getText().toString().trim(), threshold);
                threshold = th;
                String st = etSensor.getText().toString().trim();
                if (!st.isEmpty()) sensorTag = st;
                String ft = etFan.getText().toString().trim();
                if (!ft.isEmpty()) fanTag = ft;
                cloud.setBase(serverUrl);
                saveConfig();
                Toast.makeText(MainActivity.this, "设置已保存", Toast.LENGTH_SHORT).show();
            }
        });
        b.setNegativeButton("取消", null);
        b.show();
    }

    // ---------------- 风扇动画 ---------------- //

    private void buildFanAnimation() {
        fanRotAnim = new RotateAnimation(
                0f, 360f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f);
        fanRotAnim.setDuration(800);
        fanRotAnim.setRepeatCount(Animation.INFINITE);
        fanRotAnim.setInterpolator(new LinearInterpolator());
    }

    private void setFan(boolean on) {
        fanOn = on;
        if (on) {
            ivFan.startAnimation(fanRotAnim);
        } else {
            ivFan.clearAnimation();
        }
    }

    // ---------------- 模式切换 / 手动控制 ---------------- //

    private void toggleMode() {
        autoMode = !autoMode;
        tvMode.setText(autoMode ? "当前模式: 自动" : "当前模式: 手动");
        btnFanOn.setEnabled(!autoMode);
        btnFanOff.setEnabled(!autoMode);
        Toast.makeText(this, autoMode ? "已切换到自动模式" : "已切换到手动模式", Toast.LENGTH_SHORT).show();
    }

    private void manualFan(boolean on) {
        if (autoMode) {
            Toast.makeText(this, "当前为自动模式，请先切换到手动", Toast.LENGTH_SHORT).show();
            return;
        }
        setFan(on);
        sendFanCommand(on);
        Toast.makeText(this, on ? "手动开启风扇" : "手动关闭风扇", Toast.LENGTH_SHORT).show();
    }

    private void sendFanCommand(final boolean on) {
        if (devId <= 0) return;
        final int value = on ? 1 : 0;
        new Thread(new Runnable() {
            @Override public void run() { cloud.sendCommand(devId, fanTag, value); }
        }).start();
    }

    // ---------------- 数据轮询 ---------------- //

    private void startPoll() {
        stopPoll();
        pollRunnable = new Runnable() {
            @Override public void run() {
                refreshMethane();
                handler.postDelayed(this, POLL_MS);
            }
        };
        handler.post(pollRunnable);
    }

    private void stopPoll() {
        if (pollRunnable != null) {
            handler.removeCallbacks(pollRunnable);
        }
        pollRunnable = null;
    }

    private void refreshMethane() {
        if (!logged) return;
        new Thread(new Runnable() {
            @Override public void run() {
                if (devId <= 0) devId = cloud.queryFirstDeviceId();
                final Double value = cloud.fetchSensorValue(devId, sensorTag);
                handler.post(new Runnable() {
                    @Override public void run() {
                        if (value == null) {
                            tvMethane.setText("甲烷: -- %");
                            return;
                        }
                        tvMethane.setText(String.format("甲烷: %.1f %%", value));
                        // 自动模式：甲烷大于阈值开风扇(动画)，小于阈值关风扇(停动画)
                        if (autoMode) {
                            boolean shouldOn = value > threshold;
                            if (shouldOn != fanOn) {
                                setFan(shouldOn);
                                sendFanCommand(shouldOn);
                            }
                        }
                    }
                });
            }
        }).start();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopPoll();
    }
}
