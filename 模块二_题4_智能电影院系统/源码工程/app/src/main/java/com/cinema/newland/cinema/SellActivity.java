package com.cinema.newland.cinema;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

/**
 * 售卖界面（2-4 智能电影院系统）。
 *
 * 功能：
 *  - 通过中距离一体机读取 RFID 标签（电影票）。
 *  - 点击“激活电影票”把该 RFID 标记为已售。
 *  - “进入闸机”按钮跳转到首界面（EntranceActivity）。
 */
public class SellActivity extends Activity {

    private TextView tvTag;
    private TextView tvStatus;
    private Button btnRead;
    private Button btnActivate;
    private Button btnGoEntrance;

    private String currentTag = null;
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_sell);

        tvTag = findViewById(R.id.tv_tag);
        tvStatus = findViewById(R.id.tv_sell_status);
        btnRead = findViewById(R.id.btn_read_rfid);
        btnActivate = findViewById(R.id.btn_activate);
        btnGoEntrance = findViewById(R.id.btn_go_entrance);

        // 连接串口服务器（现场配置 IP/端口）
        TcpSerialClient.getInstance().setHost("172.18.0.15", 8001);

        btnRead.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                readOnce();
            }
        });

        btnActivate.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                activateTicket();
            }
        });

        btnGoEntrance.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(SellActivity.this, EntranceActivity.class));
            }
        });
    }

    /** 子线程读卡，避免阻塞 UI。 */
    private void readOnce() {
        tvStatus.setText("正在读取 RFID ...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                final String tag = RfidTicketStore.readTag();
                handler.post(new Runnable() {
                    @Override
                    public void run() {
                        if (tag == null || tag.isEmpty()) {
                            tvStatus.setText("未读到标签，请再试");
                            return;
                        }
                        currentTag = tag;
                        tvTag.setText(tag);
                        if (RfidTicketStore.isSold(SellActivity.this, tag)) {
                            tvStatus.setText("该票已售出，请勿重复激活");
                        } else {
                            tvStatus.setText("读到新票，点击“激活电影票”");
                        }
                    }
                });
            }
        }).start();
    }

    private void activateTicket() {
        if (currentTag == null || currentTag.isEmpty()) {
            Toast.makeText(this, "请先读取 RFID 电影票", Toast.LENGTH_SHORT).show();
            return;
        }
        if (RfidTicketStore.isSold(this, currentTag)) {
            Toast.makeText(this, "该票已售出", Toast.LENGTH_SHORT).show();
            return;
        }
        RfidTicketStore.markSold(this, currentTag);
        tvStatus.setText("电影票已激活（售出）：" + currentTag);
        Toast.makeText(this, "激活成功，请凭票入场", Toast.LENGTH_SHORT).show();
    }
}
