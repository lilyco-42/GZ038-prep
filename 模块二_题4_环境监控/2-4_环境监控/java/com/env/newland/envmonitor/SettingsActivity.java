package com.env.newland.envmonitor;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Environment;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class SettingsActivity extends Activity {

    private EditText etIp;
    private EditText etUhfPort;
    private EditText etAdamPort;
    private EditText etLedPort;
    private EditText etZigbeePort;
    private EditText etGreenDo;
    private EditText etFanDo;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        bindViews();
        loadPrefs();

        findViewById(R.id.btnBack).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });

        findViewById(R.id.btnSave).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                saveSettings();
            }
        });

        findViewById(R.id.btnCancel).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });
    }

    private void bindViews() {
        etIp = (EditText) findViewById(R.id.etIp);
        etUhfPort = (EditText) findViewById(R.id.etUhfPort);
        etAdamPort = (EditText) findViewById(R.id.etAdamPort);
        etLedPort = (EditText) findViewById(R.id.etLedPort);
        etZigbeePort = (EditText) findViewById(R.id.etZigbeePort);
        etGreenDo = (EditText) findViewById(R.id.etGreenDo);
        etFanDo = (EditText) findViewById(R.id.etFanDo);
    }

    private void loadPrefs() {
        SharedPreferences sp = getSharedPreferences(MainActivity.PREFS_NAME, MODE_PRIVATE);
        etIp.setText(sp.getString(MainActivity.KEY_IP, "192.168.1.100"));
        etUhfPort.setText(String.valueOf(sp.getInt("uhf_port", 6001)));
        etAdamPort.setText(String.valueOf(sp.getInt(MainActivity.KEY_DATA_PORT, 8899)));
        etLedPort.setText(String.valueOf(sp.getInt("led_port", 6003)));
        etZigbeePort.setText(String.valueOf(sp.getInt(MainActivity.KEY_CTRL_PORT, 8888)));
        etGreenDo.setText(sp.getString("green_do", "DO1"));
        etFanDo.setText(sp.getString("fan_do", "DO2"));
    }

    private void saveSettings() {
        String ip = etIp.getText().toString().trim();
        if (ip.isEmpty()) {
            toast("请输入服务器IP");
            return;
        }
        int uhf = parseIntSafe(etUhfPort.getText().toString());
        int adam = parseIntSafe(etAdamPort.getText().toString());
        int led = parseIntSafe(etLedPort.getText().toString());
        int zigbee = parseIntSafe(etZigbeePort.getText().toString());
        String greenDo = etGreenDo.getText().toString().trim();
        String fanDo = etFanDo.getText().toString().trim();

        SharedPreferences.Editor editor = getSharedPreferences(MainActivity.PREFS_NAME, MODE_PRIVATE).edit();
        editor.putString(MainActivity.KEY_IP, ip);
        editor.putInt("uhf_port", uhf);
        editor.putInt("led_port", led);
        editor.putString("green_do", greenDo);
        editor.putString("fan_do", fanDo);
        editor.putInt(MainActivity.KEY_DATA_PORT, adam);
        editor.putInt(MainActivity.KEY_CTRL_PORT, zigbee);
        editor.apply();

        hideKeyboard();
        writeConfigFile(ip, uhf, adam, led, zigbee, greenDo, fanDo);
        toast("设置已保存");
        finish();
    }

    private int parseIntSafe(String s) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return 0;
        }
    }

    private void writeConfigFile(String ip, int uhf, int adam, int led, int zigbee,
                                  String greenDo, String fanDo) {
        try {
            if (!Environment.MEDIA_MOUNTED.equals(Environment.getExternalStorageState())) return;
            String time = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.CHINA).format(new Date());
            StringBuilder sb = new StringBuilder();
            sb.append("============ 环境监控系统 连接配置 ============\n");
            sb.append("生成时间：").append(time).append("\n");
            sb.append("-----------------------------------------------------------\n");
            sb.append("串口服务器 IP：").append(ip).append("\n");
            sb.append("UHF端口：").append(uhf).append("\n");
            sb.append("数据端口(传感器数据接收)：").append(adam).append("\n");
            sb.append("LED端口：").append(led).append("\n");
            sb.append("控制端口(执行器指令发送)：").append(zigbee).append("\n");
            sb.append("三色灯(绿)：").append(greenDo).append("\n");
            sb.append("风扇：").append(fanDo).append("\n");

            File file = new File(Environment.getExternalStorageDirectory(), "C-3-1.txt");
            FileOutputStream fos = new FileOutputStream(file);
            fos.write(sb.toString().getBytes("UTF-8"));
            fos.flush();
            fos.close();
        } catch (Exception e) {
            // ignore
        }
    }

    private void hideKeyboard() {
        InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.hideSoftInputFromWindow(findViewById(android.R.id.content).getWindowToken(), 0);
        }
    }

    private void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show();
    }
}
