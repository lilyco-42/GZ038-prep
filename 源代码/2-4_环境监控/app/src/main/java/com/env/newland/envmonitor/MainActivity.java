package com.env.newland.envmonitor;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.CompoundButton;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.ToggleButton;

import java.util.Locale;
import java.util.Map;

public class MainActivity extends Activity {

    public static final String PREFS_NAME = "env_settings";
    public static final String KEY_IP = "server_ip";
    public static final String KEY_DATA_PORT = "data_port";
    public static final String KEY_CTRL_PORT = "ctrl_port";

    private static final String[] SENSORS = { "温度", "湿度", "光照度", "人体" };
    private static final String[] OPS = { "大于", "小于", "等于", "不等于" };
    private static final String[] ACTUATORS = { "绿灯", "LED灯", "风扇" };

    private CircularGaugeView gaugeTemp, gaugeHum, gaugeLight, gaugeHuman;
    private Spinner spRule1Sensor, spRule1Op, spRule1Actuator;
    private Spinner spRule2Sensor, spRule2Op, spRule2Actuator;
    private EditText etRule1Threshold, etRule2Threshold;
    private ToggleButton tbRule1Switch, tbRule2Switch;
    private ImageView ivRule1Icon, ivRule2Icon;
    private ToggleButton tbLogic;
    private TextView tvDemoBadge;

    private final TcpClient tcp = new TcpClient();
    private final Handler handler = new Handler();

    private String serverIp = "192.168.1.100";
    private int dataPort = 8899;
    private int ctrlPort = 8888;

    private double curTemp = Double.NaN;
    private double curHum = Double.NaN;
    private double curLight = Double.NaN;
    private double curHuman = Double.NaN;
    private long lastDataTime = 0;
    private boolean demoMode = false;
    private boolean autoMode = false;

    private final boolean[] actuatorState = { false, false, false };

    private final Runnable timerRunnable = new Runnable() {
        @Override
        public void run() {
            updateGauges();
            detectDemo();
            if (autoMode) {
                runAutoLogic();
            }
            handler.postDelayed(this, 1000);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        bindViews();
        setupSpinners();
        hookupControls();
        updateGauges();

        handler.post(timerRunnable);
    }

    private void bindViews() {
        gaugeTemp = (CircularGaugeView) findViewById(R.id.gaugeTemp);
        gaugeHum = (CircularGaugeView) findViewById(R.id.gaugeHum);
        gaugeLight = (CircularGaugeView) findViewById(R.id.gaugeLight);
        gaugeHuman = (CircularGaugeView) findViewById(R.id.gaugeHuman);

        spRule1Sensor = (Spinner) findViewById(R.id.spRule1Sensor);
        spRule1Op = (Spinner) findViewById(R.id.spRule1Op);
        spRule1Actuator = (Spinner) findViewById(R.id.spRule1Actuator);
        etRule1Threshold = (EditText) findViewById(R.id.etRule1Threshold);
        tbRule1Switch = (ToggleButton) findViewById(R.id.tbRule1Switch);
        ivRule1Icon = (ImageView) findViewById(R.id.ivRule1Icon);

        spRule2Sensor = (Spinner) findViewById(R.id.spRule2Sensor);
        spRule2Op = (Spinner) findViewById(R.id.spRule2Op);
        spRule2Actuator = (Spinner) findViewById(R.id.spRule2Actuator);
        etRule2Threshold = (EditText) findViewById(R.id.etRule2Threshold);
        tbRule2Switch = (ToggleButton) findViewById(R.id.tbRule2Switch);
        ivRule2Icon = (ImageView) findViewById(R.id.ivRule2Icon);

        tbLogic = (ToggleButton) findViewById(R.id.tbLogic);
        tvDemoBadge = (TextView) findViewById(R.id.tvDemoBadge);
    }

    private void setupSpinners() {
        setSpinner(spRule1Sensor, SENSORS);
        setSpinner(spRule1Op, OPS);
        setSpinner(spRule1Actuator, ACTUATORS);
        setSpinner(spRule2Sensor, SENSORS);
        setSpinner(spRule2Op, OPS);
        setSpinner(spRule2Actuator, ACTUATORS);

        spRule1Op.setSelection(1);
        spRule2Op.setSelection(0);
        spRule1Actuator.setSelection(0);
        spRule2Actuator.setSelection(2);

        spRule1Actuator.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                updateActuatorIcon(0, position);
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        spRule2Actuator.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                updateActuatorIcon(1, position);
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });
    }

    private void setSpinner(Spinner spinner, String[] items) {
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, items);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
    }

    private void updateActuatorIcon(int ruleIdx, int actuatorIdx) {
        ImageView iv = ruleIdx == 0 ? ivRule1Icon : ivRule2Icon;
        boolean on = actuatorState[actuatorIdx];
        int res;
        if (actuatorIdx == 0) {
            res = on ? R.drawable.ic_green_on : R.drawable.ic_green_off;
        } else if (actuatorIdx == 1) {
            res = on ? R.drawable.ic_led_on : R.drawable.ic_led_off;
        } else {
            res = on ? R.drawable.ic_fan_on : R.drawable.ic_fan_off;
        }
        iv.setImageResource(res);
    }

    private void hookupControls() {
        findViewById(R.id.btnSettings).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(MainActivity.this, SettingsActivity.class));
            }
        });

        tbLogic.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                autoMode = isChecked;
                Toast.makeText(MainActivity.this,
                        isChecked ? "自动逻辑模式" : "手动模式",
                        Toast.LENGTH_SHORT).show();
            }
        });

        tbRule1Switch.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                if (!autoMode) {
                    int idx = spRule1Actuator.getSelectedItemPosition();
                    changeActuator(idx, isChecked);
                }
            }
        });

        tbRule2Switch.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                if (!autoMode) {
                    int idx = spRule2Actuator.getSelectedItemPosition();
                    changeActuator(idx, isChecked);
                }
            }
        });


        tcp.setLineListener(new TcpClient.OnLineListener() {
            @Override
            public void onLine(final String raw) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        Map<String, Double> data = DataParser.parse(raw);
                        if (data.containsKey("temp")) curTemp = data.get("temp");
                        if (data.containsKey("humidity")) curHum = data.get("humidity");
                        if (data.containsKey("light")) curLight = data.get("light");
                        if (data.containsKey("human")) curHuman = data.get("human");
                        lastDataTime = System.currentTimeMillis();
                        if (demoMode) {
                            demoMode = false;
                            tcp.stopDemo();
                            tvDemoBadge.setVisibility(View.GONE);
                        }
                        updateGauges();
                    }
                });
            }
        });

        tcp.setStatusListener(new TcpClient.OnStatusListener() {
            @Override
            public void onStatusChanged(final boolean ok) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                    }
                });
            }
        });
    }

    private void changeActuator(int idx, boolean on) {
        if (idx < 0 || idx > 2) return;
        actuatorState[idx] = on;
        String cmd = cmdFor(ACTUATORS[idx], on);
        if (cmd != null) {
            tcp.sendCmd(serverIp, ctrlPort, cmd);
        }
        updateActuatorIcon(0, spRule1Actuator.getSelectedItemPosition());
        updateActuatorIcon(1, spRule2Actuator.getSelectedItemPosition());
    }

    private void runAutoLogic() {
        boolean[] should = { false, false, false };
        evalRule(spRule1Sensor, spRule1Op, etRule1Threshold, spRule1Actuator, tbRule1Switch, should);
        evalRule(spRule2Sensor, spRule2Op, etRule2Threshold, spRule2Actuator, tbRule2Switch, should);
        for (int i = 0; i < 3; i++) {
            if (should[i] != actuatorState[i]) {
                changeActuator(i, should[i]);
            }
        }
    }

    private void evalRule(Spinner spSensor, Spinner spOp, EditText etThreshold,
                          Spinner spActuator, ToggleButton tbSwitch, boolean[] should) {
        int sensorIdx = spSensor.getSelectedItemPosition();
        int opIdx = spOp.getSelectedItemPosition();
        int actIdx = spActuator.getSelectedItemPosition();
        double threshold;
        try {
            threshold = Double.parseDouble(etThreshold.getText().toString().trim());
        } catch (NumberFormatException e) {
            return;
        }
        double val;
        switch (sensorIdx) {
            case 0: val = curTemp; break;
            case 1: val = curHum; break;
            case 2: val = curLight; break;
            case 3: val = curHuman; break;
            default: return;
        }
        if (Double.isNaN(val)) return;
        boolean match = false;
        switch (opIdx) {
            case 0: match = val > threshold; break;
            case 1: match = val < threshold; break;
            case 2: match = Math.abs(val - threshold) < 0.001; break;
            case 3: match = Math.abs(val - threshold) >= 0.001; break;
        }
        if (match) {
            should[actIdx] = true;
        }
        tbSwitch.setChecked(match);
    }

    private void updateGauges() {
        gaugeTemp.setGauge(Color.parseColor("#00BCD4"), "温度",
                Double.isNaN(curTemp) ? "0°C" : String.format(Locale.CHINA, "%.1f°C", curTemp));
        gaugeHum.setGauge(Color.parseColor("#4CAF50"), "湿度",
                Double.isNaN(curHum) ? "0%" : String.format(Locale.CHINA, "%.0f%%", curHum));
        gaugeLight.setGauge(Color.parseColor("#FFB300"), "光照",
                Double.isNaN(curLight) ? "0lx" : String.format(Locale.CHINA, "%.0flx", curLight));
        String humanText = Double.isNaN(curHuman) ? "无人" : (curHuman > 0.5 ? "有人" : "无人");
        int humanColor = (!Double.isNaN(curHuman) && curHuman > 0.5) ?
                Color.parseColor("#FF5252") : Color.parseColor("#FF5252");
        gaugeHuman.setGauge(humanColor, "人体", humanText);
    }

    private void detectDemo() {
        if (!demoMode && System.currentTimeMillis() - lastDataTime > 4000L) {
            demoMode = true;
            tcp.startDemo();
            tvDemoBadge.setVisibility(View.VISIBLE);
        }
    }

    private static String cmdFor(String actuator, boolean on) {
        String base = null;
        if ("绿灯".equals(actuator)) base = "green";
        else if ("LED灯".equals(actuator)) base = "led";
        else if ("风扇".equals(actuator)) base = "fan";
        return base != null ? base + (on ? "_on\n" : "_off\n") : null;
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadSettingsAndApply();
        tcp.stop();
        tcp.start();
    }

    private void loadSettingsAndApply() {
        SharedPreferences sp = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        serverIp = sp.getString(KEY_IP, "192.168.1.100");
        dataPort = sp.getInt(KEY_DATA_PORT, 8899);
        ctrlPort = sp.getInt(KEY_CTRL_PORT, 8888);
        tcp.setDataAddress(serverIp, dataPort);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        handler.removeCallbacks(timerRunnable);
        tcp.stop();
    }
}
