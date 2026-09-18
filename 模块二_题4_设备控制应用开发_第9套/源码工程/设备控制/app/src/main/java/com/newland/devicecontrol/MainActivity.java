package com.newland.devicecontrol;

import android.app.AlertDialog;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import android.support.v7.app.AppCompatActivity;

/**
 * 子任务2-4 设备控制应用
 *   - "LED灯"选开启/关闭 -> 控制工位照明灯(常亮绿灯)开/关;
 *   - "风扇" 选开启/关闭 -> 控制工位风扇 开/停;
 *   - 通过物联网云服务系统下发指令。
 *
 * 传感器/执行器标识(对应模块一表):
 *   照明灯(常亮绿灯) -> m_steady_green
 *   风扇             -> m_fan
 * 若工位标识不同, 在下方常量或界面中修改即可。
 */
public class MainActivity extends AppCompatActivity {

    /** 执行器标识: 照明灯 / 风扇 */
    private static final String TAG_LIGHT = "m_steady_green";
    private static final String TAG_FAN   = "m_fan";

    private EditText etHost, etAccount, etPwd;
    private Button btnLogin;
    private TextView tvStatus, tvConnDot;

    private Button lightOn, lightOff, fanOn, fanOff;
    private TextView lightState, fanState;

    private CloudClient cloud;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private boolean loggedIn = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        if (getSupportActionBar() != null) getSupportActionBar().setTitle("设备控制");

        etHost    = findViewById(R.id.et_host);
        etAccount = findViewById(R.id.et_account);
        etPwd     = findViewById(R.id.et_pwd);
        btnLogin  = findViewById(R.id.btn_login);
        tvStatus  = findViewById(R.id.tv_status);
        tvConnDot = findViewById(R.id.tv_conn_dot);

        lightOn   = findViewById(R.id.light_on);
        lightOff  = findViewById(R.id.light_off);
        fanOn     = findViewById(R.id.fan_on);
        fanOff    = findViewById(R.id.fan_off);
        lightState= findViewById(R.id.light_state);
        fanState  = findViewById(R.id.fan_state);

        btnLogin.setOnClickListener(v -> doLogin());
        lightOn.setOnClickListener(v -> controlLight(1));
        lightOff.setOnClickListener(v -> controlLight(0));
        fanOn.setOnClickListener(v -> controlFan(1));
        fanOff.setOnClickListener(v -> controlFan(0));

        setConn(false);
    }

    /** 登录云服务系统(后台线程) */
    private void doLogin() {
        final String host = etHost.getText().toString().trim();
        final String acc  = etAccount.getText().toString().trim();
        final String pwd  = etPwd.getText().toString().trim();
        if (host.isEmpty() || acc.isEmpty() || pwd.isEmpty()) {
            toast("请填写服务器地址、账号、密码");
            return;
        }
        tvStatus.setText("正在登录 " + host + " ...");
        new Thread(() -> {
            cloud = new CloudClient("http://" + host);
            boolean ok = cloud.login(acc, pwd);
            if (ok) ok = cloud.bindFirstDevice() >= 0;
            final boolean res = ok;
            ui.post(() -> {
                loggedIn = res;
                setConn(res);
                tvStatus.setText(res ? "已登录, 可控制设备" : "登录失败, 请检查地址/账号/密码");
            });
        }).start();
    }

    /** 控制照明灯: value=1开 0关 */
    private void controlLight(final int value) {
        if (!ensureLogin()) return;
        send(TAG_LIGHT, value, lightState, value == 1 ? "照明灯已开" : "照明灯已关");
    }

    /** 控制风扇: value=1开 0关 */
    private void controlFan(final int value) {
        if (!ensureLogin()) return;
        send(TAG_FAN, value, fanState, value == 1 ? "风扇已启动" : "风扇已停止");
    }

    private boolean ensureLogin() {
        if (!loggedIn || cloud == null) {
            toast("请先登录云服务系统");
            return false;
        }
        return true;
    }

    private void send(final String tag, final int value, final TextView stateView, final String okMsg) {
        tvStatus.setText("下发: " + tag + " = " + value);
        new Thread(() -> {
            boolean ok = cloud.sendCommand(tag, value);
            ui.post(() -> {
                if (ok) {
                    stateView.setText(value == 1 ? "开" : "关");
                    stateView.setTextColor(value == 1 ? Color.parseColor("#4CAF50") : Color.parseColor("#999999"));
                    toast(okMsg);
                    tvStatus.setText(okMsg);
                } else {
                    toast("指令下发失败");
                    tvStatus.setText("指令下发失败");
                }
            });
        }).start();
    }

    private void setConn(boolean ok) {
        tvConnDot.setText(ok ? "已连接" : "未连接");
        tvConnDot.setTextColor(ok ? Color.parseColor("#4CAF50") : Color.parseColor("#999999"));
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }
}
