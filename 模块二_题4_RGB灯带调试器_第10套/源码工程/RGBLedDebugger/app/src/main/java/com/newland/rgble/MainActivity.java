package com.newland.rgble;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.CompoundButton;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

/**
 * 子任务2-4 RGB 灯带调试器。
 *
 * 业务规则:
 *  - 界面上半部分用一个大色块实时显示当前 R/G/B 混合后的灯带颜色。
 *  - R/G/B 三条颜色条(SeekBar, 范围 0~255), 拖动实时改变对应通道值并刷新色块与数值。
 *  - R/G/B 通道值实时显示在界面对应标签右侧。
 *  - 仅当"灯带开关"打开后, 才把当前 R/G/B 值下发到工位 RGB 灯带(m_rgb_red/green/blue);
 *    开关关闭时只刷新界面预览, 不下发。
 *  - 退出 App 时关闭灯带(三色均下发 0)。
 */
public class MainActivity extends Activity {

    /* 云服务设备标识(ApiTag), 与云服务系统录入保持一致 */
    private static final String TAG_RED   = "m_rgb_red";    // RGB灯带-红
    private static final String TAG_GREEN = "m_rgb_green";  // RGB灯带-绿
    private static final String TAG_BLUE  = "m_rgb_blue";  // RGB灯带-蓝

    /* 云服务连接参数(按工位实际修改) */
    private static final String CLOUD_URL = "http://192.168.0.138";
    private static final String CLOUD_USER = "18912345600";
    private static final String CLOUD_PWD  = "123456";

    private CloudClient cloud;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private ViewHolder ui = new ViewHolder();

    /* 当前通道值 */
    private int r = 0, g = 0, b = 0;
    private boolean lampOn = false;

    /* 上一次下发值, 避免重复下发 */
    private int lastRed = -1, lastGreen = -1, lastBlue = -1;

    static class ViewHolder {
        TextView colorPanel;       // 上半部分实时颜色块
        SeekBar sbR, sbG, sbB;     // 红/绿/蓝 颜色条 0~255
        TextView tvR, tvG, tvB;    // 实时数值
        Switch swLamp;             // 灯带总开关
        TextView tvStatus;         // 状态提示
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        ui.colorPanel = findViewById(R.id.color_panel);
        ui.sbR = findViewById(R.id.sb_red);
        ui.sbG = findViewById(R.id.sb_green);
        ui.sbB = findViewById(R.id.sb_blue);
        ui.tvR = findViewById(R.id.tv_red_value);
        ui.tvG = findViewById(R.id.tv_green_value);
        ui.tvB = findViewById(R.id.tv_blue_value);
        ui.swLamp = findViewById(R.id.sw_lamp);
        ui.tvStatus = findViewById(R.id.tv_status);

        ui.sbR.setMax(255);
        ui.sbG.setMax(255);
        ui.sbB.setMax(255);

        cloud = new CloudClient(CLOUD_URL);
        /* 登录放后台线程, 避免阻塞 UI */
        new Thread(new Runnable() {
            @Override public void run() {
                final boolean ok = cloud.login(CLOUD_USER, CLOUD_PWD);
                if (ok) cloud.bindFirstDevice();
                handler.post(new Runnable() {
                    @Override public void run() {
                        ui.tvStatus.setText(ok ? "云服务已连接" : "云服务未连接(仅本地预览)");
                    }
                });
            }
        }).start();

        /* 颜色条拖动监听 */
        SeekBar.OnSeekBarChangeListener l = new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar sb, int progress, boolean fromUser) {
                if (sb == ui.sbR) r = progress;
                else if (sb == ui.sbG) g = progress;
                else if (sb == ui.sbB) b = progress;
                refreshUi();
                pushIfOn();
            }
            @Override public void onStartTrackingTouch(SeekBar sb) {}
            @Override public void onStopTrackingTouch(SeekBar sb) {}
        };
        ui.sbR.setOnSeekBarChangeListener(l);
        ui.sbG.setOnSeekBarChangeListener(l);
        ui.sbB.setOnSeekBarChangeListener(l);

        /* 灯带总开关 */
        ui.swLamp.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override public void onCheckedChanged(CompoundButton btn, boolean checked) {
                lampOn = checked;
                ui.tvStatus.setText(checked ? "灯带已开启" : "灯带已关闭");
                pushIfOn();
                /* 关闭开关时关灯 */
                if (!checked) pushOff();
            }
        });

        refreshUi();
    }

    /** 刷新色块与数值 */
    private void refreshUi() {
        int color = Color.rgb(r, g, b);
        ui.colorPanel.setBackgroundColor(color);
        /* 深色块上用白字, 浅色块上用黑字, 保证可读 */
        int lum = (int) (0.299 * r + 0.587 * g + 0.114 * b);
        ui.colorPanel.setTextColor(lum > 140 ? Color.BLACK : Color.WHITE);
        ui.colorPanel.setText(String.format("当前颜色\nRGB(%d, %d, %d)", r, g, b));
        ui.tvR.setText(String.valueOf(r));
        ui.tvG.setText(String.valueOf(g));
        ui.tvB.setText(String.valueOf(b));
    }

    /** 开关开启时才下发到灯带 */
    private void pushIfOn() {
        if (!lampOn) return;
        pushChannel(TAG_RED, r, true);
        pushChannel(TAG_GREEN, g, false);
        pushChannel(TAG_BLUE, b, false);
    }

    private void pushChannel(final String tag, final int value, final boolean first) {
        int last = first ? lastRed : (tag.equals(TAG_GREEN) ? lastGreen : lastBlue);
        if (last == value) return;
        new Thread(new Runnable() {
            @Override public void run() { cloud.sendCommand(tag, value); }
        }).start();
        if (first) lastRed = value;
        else if (tag.equals(TAG_GREEN)) lastGreen = value;
        else lastBlue = value;
    }

    /** 关闭灯带: 三色均下发 0 */
    private void pushOff() {
        new Thread(new Runnable() {
            @Override public void run() {
                cloud.sendCommand(TAG_RED, 0);
                cloud.sendCommand(TAG_GREEN, 0);
                cloud.sendCommand(TAG_BLUE, 0);
            }
        }).start();
        lastRed = lastGreen = lastBlue = -1;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        pushOff();
    }
}
