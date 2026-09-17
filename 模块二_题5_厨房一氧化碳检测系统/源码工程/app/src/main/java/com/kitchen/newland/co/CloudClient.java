package com.kitchen.newland.co;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * 物联网云服务系统(nlecloud) REST 客户端（2-5 厨房一氧化碳检测系统）。
 *
 * 功能：
 *  1. users/login 登录拿 AccessToken；
 *  2. 读取传感器 l_co（一氧化碳）最新值（NS(LoRa)+LoRa网关 5s 上报一次）；
 *  3. 向执行器下发指令：风扇 z_fan、窗户电动推杆（伸出/收回）。
 *
 * 与仓库 Python nle_cloud.py 接口一致，仅用 Java 重写。
 */
public class CloudClient {

    private String baseUrl = "http://192.168.0.138";
    private String account = "";
    private String password = "";
    private String token = null;

    // 设备/标识配置（现场按云项目填写）
    public String coTag = "l_co";          // 一氧化碳传感器标识
    public String fanTag = "z_fan";        // ZigBee 风扇
    public String pushrodPut = "m_pushrod_putt";   // 推杆伸出（开窗）
    public String pushrodBack = "m_pushrod_back";  // 推杆收回（关窗）

    public void setAccount(String base, String account, String password) {
        this.baseUrl = (base == null ? "" : base).replaceAll("/+$", "");
        this.account = account;
        this.password = password;
    }

    /** 登录，成功返回 true。 */
    public synchronized boolean login() {
        try {
            JSONObject body = new JSONObject();
            body.put("Account", account);
            body.put("Password", password);
            body.put("IsRememberMe", true);
            String resp = httpPost("/users/login", body.toString(), null);
            JSONObject json = new JSONObject(resp);
            JSONObject result = json.optJSONObject("ResultObj");
            if (result != null) {
                token = result.optString("AccessToken", null);
            }
            return token != null && token.length() > 0;
        } catch (Exception e) {
            return false;
        }
    }

    /** 读取 l_co 最新值，失败返回 -1。 */
    public synchronized double readCo() {
        try {
            // 实际工程：先 /Devices 查询网关 DeviceID，再 /Devices/Datas 批量取数；
            // 这里给出读取某传感器最新值的占位实现，现场按 SDK 补全。
            // JSONObject devs = httpGet("/Devices/Datas?devIds=" + devId);
            // 遍历 Datas 找 ApiTag == coTag 的 Value。
            return Double.NaN;
        } catch (Exception e) {
            return Double.NaN;
        }
    }

    /** 下发执行器指令。on=true 打开/伸出，false 关闭/收回。 */
    public synchronized boolean sendCommand(String apiTag, int value) {
        try {
            JSONObject body = new JSONObject();
            body.put("apikey", token == null ? "" : token);
            body.put("apitag", apiTag);
            body.put("value", value);
            String resp = httpPost("/Devices/" + deviceIdForCmd() + "/Cmds",
                    body.toString(), token);
            JSONObject json = new JSONObject(resp);
            int status = json.optInt("StatusCode", 0);
            return status == 1 || status == 2;
        } catch (Exception e) {
            return false;
        }
    }

    private String deviceIdForCmd() {
        return "1"; // 现场替换为执行器所在设备 DeviceID
    }

    // ---------------- HTTP 工具 ----------------
    private String httpGet(String path) throws Exception {
        return request("GET", path, null, token);
    }

    private String httpPost(String path, String body, String tk) throws Exception {
        return request("POST", path, body, tk);
    }

    private String request(String method, String path, String body, String tk) throws Exception {
        URL url = new URL(baseUrl + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod(method);
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(5000);
        conn.setRequestProperty("Content-Type", "application/json");
        if (tk != null) conn.setRequestProperty("AccessToken", tk);
        if (body != null) {
            conn.setDoOutput(true);
            OutputStream os = conn.getOutputStream();
            os.write(body.getBytes("UTF-8"));
            os.flush();
            os.close();
        }
        InputStream is = conn.getInputStream();
        BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line);
        br.close();
        return sb.toString();
    }
}
