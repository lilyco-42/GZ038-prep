package com.newland.product;

import android.app.Activity;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.text.TextUtils;
import android.view.KeyEvent;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * 子任务2-5 商品查询系统。
 *
 * 功能:
 *  1. 内置三个商品: 华为mate20/5999、IPhoneXS/2299、小米Mix3/7699,
 *     每个商品对应一张超高频电子标签(EPC)。
 *  2. 用中距离一体机(UHF RFID)读取标签, 或用扫描枪扫描打印出来的商品条码;
 *  3. 读到任一标签/条码后, 在界面显示对应商品名称与价格,
 *     并用 TTS 语音播报商品名称和价格。
 */
public class MainActivity extends Activity {

    /** 标签/条码 -> 商品信息 */
    private final Map<String, Product> productMap = new HashMap<String, Product>();

    private TextView tvName, tvPrice, tvTag, tvHint;
    private TextToSpeech tts;

    /** 扫描枪(键盘 wedge)输入缓冲: 扫码枪回车结束一帧 */
    private final StringBuilder scanBuffer = new StringBuilder();

    private RfidReader rfid;
    private boolean running = false;

    static class Product {
        String tag, name, price;
        Product(String t, String n, String p) { tag = t; name = n; price = p; }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvName = findViewById(R.id.tv_name);
        tvPrice = findViewById(R.id.tv_price);
        tvTag = findViewById(R.id.tv_tag);
        tvHint = findViewById(R.id.tv_hint);

        loadProducts();
        initTts();
        initRfid();
    }

    /** 从 assets/products.json 装载商品表 */
    private void loadProducts() {
        try {
            InputStream is = getAssets().open("products.json");
            BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line);
            br.close();
            JSONArray arr = new JSONArray(sb.toString());
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                Product p = new Product(o.optString("tag"),
                        o.optString("name"), o.optString("price"));
                productMap.put(p.tag.toUpperCase(Locale.getDefault()), p);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void initTts() {
        tts = new TextToSpeech(this, new TextToSpeech.OnInitListener() {
            @Override public void onInit(int status) {
                if (status == TextToSpeech.SUCCESS) {
                    tts.setLanguage(Locale.CHINESE);
                }
            }
        });
    }

    /** 初始化中距离一体机 UHF 读头; 无设备时回退模拟轮询 */
    private void initRfid() {
        rfid = new RfidReader();
        running = true;
        new Thread(new Runnable() {
            @Override public void run() {
                while (running) {
                    final String epc = rfid.readOne();
                    if (!TextUtils.isEmpty(epc)) {
                        runOnUiThread(new Runnable() {
                            @Override public void run() { onCodeRead(epc); }
                        });
                    }
                    try { Thread.sleep(200); } catch (InterruptedException ignored) {}
                }
            }
        }).start();
    }

    /** 读到一个编码(标签EPC 或 扫描枪条码)后的统一处理 */
    private void onCodeRead(String code) {
        if (TextUtils.isEmpty(code)) return;
        String key = code.trim().toUpperCase(Locale.getDefault());
        Product p = productMap.get(key);

        tvTag.setText(code);
        if (p == null) {
            tvName.setText("未登记商品");
            tvPrice.setText("--");
            tvHint.setText("未知标签, 请先登记");
            tvHint.setTextColor(0xFFC62828);
            speak("未登记商品");
        } else {
            tvName.setText(p.name);
            tvPrice.setText(p.price + " 元");
            tvHint.setText("识别成功");
            tvHint.setTextColor(0xFF2E7D32);
            // 播报: 商品名称、价格
            speak(p.name + ", 价格 " + p.price + " 元");
        }
    }

    private void speak(String text) {
        if (tts != null) tts.speak(text, TextToSpeech.QUEUE_FLUSH, null);
    }

    /** 扫描枪作为键盘 wedge: 收集按键, 回车表示一帧结束 */
    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int c = event.getUnicodeChar();
            if (event.getKeyCode() == KeyEvent.KEYCODE_ENTER) {
                String code = scanBuffer.toString();
                scanBuffer.setLength(0);
                if (!TextUtils.isEmpty(code)) onCodeRead(code);
                return true;
            } else if (c > 0 && c < 128) {
                scanBuffer.append((char) c);
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        running = false;
        if (rfid != null) rfid.close();
        if (tts != null) { tts.stop(); tts.shutdown(); }
    }
}
