package com.cinema.newland.cinema;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;
import android.widget.Toast;

/**
 * 首界面 / 闸机界面（2-4 智能电影院系统）。
 *
 * 功能：
 *  - 实时循环读取 RFID 标签。
 *  - 感应到“已售（已激活）”的 RFID 后：
 *      1) 自动打开闸门（电动推杆伸出）；
 *      2) 3 秒后自动关闭闸门（电动推杆收回）；
 *      3) 自动跳转到影院主界面（MainActivity）。
 *  - 未售出/无效标签：提示无效，不开闸。
 */
public class EntranceActivity extends Activity {

    private TextView tvTip;
    private TextView tvGateState;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private volatile boolean reading = true;
    private volatile boolean gateBusy = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_entrance);

        tvTip = findViewById(R.id.tv_tip);
        tvGateState = findViewById(R.id.tv_gate_state);

        TcpSerialClient.getInstance().setHost("172.18.0.15", 8001);
        startReadLoop();
    }

    private void startReadLoop() {
        reading = true;
        new Thread(new Runnable() {
            @Override
            public void run() {
                while (reading && !gateBusy) {
                    try {
                        final String tag = RfidTicketStore.readTag();
                        if (tag != null && !tag.isEmpty()) {
                            final boolean sold = RfidTicketStore.isSold(EntranceActivity.this, tag);
                            handler.post(new Runnable() {
                                @Override
                                public void run() {
                                    onReadTag(tag, sold);
                                }
                            });
                        }
                        Thread.sleep(300);
                    } catch (InterruptedException e) {
                        break;
                    } catch (Exception ignored) {
                    }
                }
            }
        }).start();
    }

    private void onReadTag(String tag, boolean sold) {
        if (!sold) {
            tvTip.setText("无效票（未售出），请先到售票处激活");
            Toast.makeText(this, "无效票：" + tag, Toast.LENGTH_SHORT).show();
            return;
        }
        // 命中已售票 -> 开闸
        gateBusy = true;
        tvTip.setText("检票通过，欢迎入场！");
        tvGateState.setText("闸门：开启");
        TcpSerialClient.getInstance().controlGate(true);   // 推杆伸开出闸

        // 3 秒后关闸并跳主界面
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                TcpSerialClient.getInstance().controlGate(false); // 推杆收回关闸
                tvGateState.setText("闸门：关闭");
                startActivity(new Intent(EntranceActivity.this, MainActivity.class));
                finish();
            }
        }, 3000);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        reading = false;
    }
}
