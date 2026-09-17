package com.newland.envmonitor;

/**
 * 环境监控（云服务系统应用开发 - 子任务2-4）——官方库版
 *
 * 仿照官方例程 nle_hardware_v1/AllInOne + ZigBee 模板重写：
 *   1. TCP 连接串口服务器/网关（DataBusFactory.newSocketDataBus）
 *   2. 多合一传感器采集：温湿度 / 人体 / PM2.5 / 空气质量 / 气压
 *   3. ZigBee 传感器帧解析：温湿度 / 光照 / 人体 / 火焰 / 四输入(CO2等)
 *   4. ZigBee 继电器控制：风扇 / LED 照明灯
 *
 * 依赖：app/libs/nle_hardware_v1.jar + gson-2.8.1.jar（官方二进制，U盘/官方例程 依赖 目录获取）
 */

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.nle.mylibrary.claimer.connector.ConnectorListener;
import com.nle.mylibrary.claimer.zigbee.FourChannelValConvert;
import com.nle.mylibrary.databus.DataBus;
import com.nle.mylibrary.databus.DataBusFactory;
import com.nle.mylibrary.databus.ReciveData;
import com.nle.mylibrary.device.GenericConnector;
import com.nle.mylibrary.device.ZigBee3;
import com.nle.mylibrary.device.listener.ConnectResultListener;
import com.nle.mylibrary.enums.zigBee.ZigBeeSensorType;

import java.util.concurrent.TimeUnit;

@SuppressLint("SetTextI18n")
public class MainActivity extends AppCompatActivity implements View.OnClickListener {

    private static final String TAG = "EnvMonitor";

    private Handler handler;
    private DataBus dataBus;
    private GenericConnector genericConnector;
    private String ip;
    private int port;
    private int address;

    // ZigBee 双联继电器短地址（赛题工位默认 0x141d，按实际修改）
    private static final int RELAY_SERIAL = 0x141d;
    // 双联继电器指令：0x11 全开 | 0x22 全关 | 0x21 一开二关 | 0x12 一关二开
    // 约定：通道1 = 风扇，通道2 = LED 照明灯
    private boolean fanOn = false;
    private boolean ledOn = false;

    private TextView sensor1Value, sensor2Value, sensor3Value, sensor4Value, sensor5Value, sensor6Value;
    private TextView fanStateText, ledStateText;
    private EditText IPEdit, PortEdit;
    private Button LinkBtn, FanOnBtn, FanOffBtn, LedOnBtn, LedOffBtn;

    private final Thread sensorThread = new Thread(new Runnable() {
        @Override
        public void run() {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    TimeUnit.MILLISECONDS.sleep(500);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }
    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_HIDDEN);

        handler = new Handler(Looper.getMainLooper());
        bind();
    }

    private void bind() {
        sensor1Value = findViewById(R.id.sensor1Value);
        sensor2Value = findViewById(R.id.sensor2Value);
        sensor3Value = findViewById(R.id.sensor3Value);
        sensor4Value = findViewById(R.id.sensor4Value);
        sensor5Value = findViewById(R.id.sensor5Value);
        sensor6Value = findViewById(R.id.sensor6Value);
        fanStateText = findViewById(R.id.fanStateText);
        ledStateText = findViewById(R.id.ledStateText);
        IPEdit = findViewById(R.id.IPEdit);
        PortEdit = findViewById(R.id.PortEdit);
        LinkBtn = findViewById(R.id.LinkBtn);
        FanOnBtn = findViewById(R.id.FanOnBtn);
        FanOffBtn = findViewById(R.id.FanOffBtn);
        LedOnBtn = findViewById(R.id.LedOnBtn);
        LedOffBtn = findViewById(R.id.LedOffBtn);

        // 默认赛场参数（串口服务器 TCP 模式）
        IPEdit.setText("192.168.1.200");
        PortEdit.setText("8899");

        LinkBtn.setOnClickListener(this);
        FanOnBtn.setOnClickListener(this);
        FanOffBtn.setOnClickListener(this);
        LedOnBtn.setOnClickListener(this);
        LedOffBtn.setOnClickListener(this);
    }

    private void updateSensor(final int index, final String value) {
        handler.post(new Runnable() {
            @Override
            public void run() {
                switch (index) {
                    case 1: sensor1Value.setText(value); break;
                    case 2: sensor2Value.setText(value); break;
                    case 3: sensor3Value.setText(value); break;
                    case 4: sensor4Value.setText(value); break;
                    case 5: sensor5Value.setText(value); break;
                    case 6: sensor6Value.setText(value); break;
                }
            }
        });
    }

    /**
     * 连接串口服务器（TCP）并注册 ZigBee 数据监听
     */
    private void connect() {
        ip = IPEdit.getText().toString().trim();
        port = Integer.parseInt(PortEdit.getText().toString().trim());
        dataBus = DataBusFactory.newSocketDataBus(ip, port);
        // ZigBee 传感器帧解析（官方 ZigBee 模板写法）
        dataBus.setReciveDataListener(new ReciveData() {
            @Override
            public String getReciveData(byte[] bytes) {
                try {
                    ZigBee3 zigBee3 = new ZigBee3(bytes);
                    // 温湿度
                    if (zigBee3.sensorType() == ZigBeeSensorType.TEM_HUM.getCode()) {
                        updateSensor(1, String.format("%.2f", zigBee3.getVal0()));
                        updateSensor(2, String.format("%.2f", zigBee3.getVal1()));
                    }
                    // 光照
                    else if (zigBee3.sensorType() == ZigBeeSensorType.LIGHT.getCode()) {
                        updateSensor(3, String.format("%.2f", zigBee3.getVal0()));
                    }
                    // 人体
                    else if (zigBee3.sensorType() == ZigBeeSensorType.PERSON.getCode()) {
                        updateSensor(4, String.format("%.2f", zigBee3.getVal0()));
                    }
                    // 火焰
                    else if (zigBee3.sensorType() == ZigBeeSensorType.FIRE.getCode()) {
                        updateSensor(5, String.format("%.2f", zigBee3.getVal0()));
                    }
                    // 四输入（CO2/噪音/水浸等，配合 FourChannelValConvert）
                    else if (zigBee3.sensorType() == ZigBeeSensorType.FOUR_ENTER.getCode()) {
                        updateSensor(6, String.format("%.2f", FourChannelValConvert.getTemperature(zigBee3.getVal0())));
                    }
                } catch (ArrayIndexOutOfBoundsException e) {
                    Log.i(TAG, "zigbee frame: " + e.toString());
                }
                return null;
            }
        });

        genericConnector = new GenericConnector(dataBus, new ConnectResultListener() {
            @Override
            public void onConnectResult(boolean b) {
                if (b) {
                    Log.i(TAG, "Link OK");
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            LinkBtn.setText("断开");
                            IPEdit.setEnabled(false);
                            PortEdit.setEnabled(false);
                            Toast.makeText(getApplication(), "连接成功", Toast.LENGTH_SHORT).show();
                        }
                    });
                    // 连接后读取多合一传感器地址（官方 AllInOne 模板写法）
                    getDeviceAddress();
                } else {
                    genericConnector = null;
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(getApplicationContext(), "连接失败", Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        });
    }

    /**
     * 获取多合一传感器设备地址，随后轮询采集各项数据
     */
    private void getDeviceAddress() {
        try {
            genericConnector.sendAllInOneGetAddress(new ConnectorListener() {
                @Override
                public void onSuccess(boolean b) {
                    address = genericConnector.getAllInOneGetAddress();
                    Log.i(TAG, "Device Address: " + address);
                    startSensorLoop();
                }

                @Override
                public void onFail(Exception e) {
                    Log.e(TAG, "get address fail", e);
                }
            });
        } catch (Exception e) {
            Log.e(TAG, "getDeviceAddress", e);
        }
    }

    private void startSensorLoop() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                while (!Thread.currentThread().isInterrupted()) {
                    try {
                        getTempHum();
                        TimeUnit.MILLISECONDS.sleep(200);
                        getBody();
                        TimeUnit.MILLISECONDS.sleep(200);
                        getPM25();
                        TimeUnit.MILLISECONDS.sleep(200);
                        getAirQuality();
                        TimeUnit.MILLISECONDS.sleep(200);
                        getPressure();
                        TimeUnit.MILLISECONDS.sleep(1000);
                    } catch (InterruptedException e) {
                        break;
                    }
                }
            }
        }).start();
    }

    /** 温湿度 */
    private void getTempHum() {
        try {
            genericConnector.sendAllInOneTempHum(address, new ConnectorListener() {
                @Override
                public void onSuccess(boolean b) {
                    updateSensor(1, String.valueOf(genericConnector.getAllInOneTemp()));
                    updateSensor(2, String.valueOf(genericConnector.getAllInOneHum()));
                }
                @Override public void onFail(Exception e) { }
            });
        } catch (Exception e) { Log.e(TAG, "TempHum", e); }
    }

    /** 人体 */
    private void getBody() {
        try {
            genericConnector.sendAllInOneBody(address, new ConnectorListener() {
                @Override
                public void onSuccess(boolean b) {
                    int body = genericConnector.getAllInOneBody();
                    updateSensor(4, body == 0 ? "无人" : "有人");
                }
                @Override public void onFail(Exception e) { }
            });
        } catch (Exception e) { Log.e(TAG, "Body", e); }
    }

    /** PM2.5 */
    private void getPM25() {
        try {
            genericConnector.sendAllInOnePM25(address, new ConnectorListener() {
                @Override
                public void onSuccess(boolean b) {
                    updateSensor(5, String.valueOf(genericConnector.getAllInOnePm25()));
                }
                @Override public void onFail(Exception e) { }
            });
        } catch (Exception e) { Log.e(TAG, "PM25", e); }
    }

    /** 空气质量 */
    private void getAirQuality() {
        try {
            genericConnector.sendAllInOneAirQuality(address, new ConnectorListener() {
                @Override
                public void onSuccess(boolean b) {
                    updateSensor(6, String.valueOf(genericConnector.getAllInOneAirQuality()));
                }
                @Override public void onFail(Exception e) { }
            });
        } catch (Exception e) { Log.e(TAG, "AirQuality", e); }
    }

    /** 气压 */
    private void getPressure() {
        try {
            genericConnector.sendAllInOnePressure(address, new ConnectorListener() {
                @Override
                public void onSuccess(boolean b) {
                    updateSensor(3, String.valueOf(genericConnector.getAllInOnePressure()));
                }
                @Override public void onFail(Exception e) { }
            });
        } catch (Exception e) { Log.e(TAG, "Pressure", e); }
    }

    /**
     * ZigBee 继电器控制（双联：通道1=风扇，通道2=LED）
     * 指令：0x11 全开 | 0x22 全关 | 0x21 一开二关 | 0x12 一关二开
     */
    private void sendRelay() {
        byte cmd;
        if (fanOn && ledOn) cmd = 0x11;        // 全开
        else if (!fanOn && !ledOn) cmd = 0x22; // 全关
        else if (fanOn) cmd = 0x21;            // 风扇开 LED 关
        else cmd = 0x12;                       // LED 开 风扇关
        try {
            genericConnector.ZigbeeControl(RELAY_SERIAL, cmd, null);
            Log.i(TAG, "Relay cmd: " + String.format("0x%02X", cmd));
        } catch (Exception e) {
            Log.e(TAG, "ZigbeeControl", e);
        }
    }

    @Override
    public void onClick(View v) {
        if (v.getId() == R.id.LinkBtn) {
            if (genericConnector == null) {
                connect();
            } else {
                genericConnector.stopConnect();
                genericConnector = null;
                IPEdit.setEnabled(true);
                PortEdit.setEnabled(true);
                LinkBtn.setText("连接");
                Toast.makeText(getApplication(), "断开连接", Toast.LENGTH_SHORT).show();
            }
        } else if (v.getId() == R.id.FanOnBtn) {
            fanOn = true; sendRelay(); fanStateText.setText("开启");
        } else if (v.getId() == R.id.FanOffBtn) {
            fanOn = false; sendRelay(); fanStateText.setText("关闭");
        } else if (v.getId() == R.id.LedOnBtn) {
            ledOn = true; sendRelay(); ledStateText.setText("开启");
        } else if (v.getId() == R.id.LedOffBtn) {
            ledOn = false; sendRelay(); ledStateText.setText("关闭");
        }
    }
}
