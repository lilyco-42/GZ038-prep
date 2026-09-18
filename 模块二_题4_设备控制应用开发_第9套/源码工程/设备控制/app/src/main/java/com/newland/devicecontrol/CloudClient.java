package com.newland.devicecontrol;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * 物联网云服务系统 (NL-Cloud) RESTful 客户端。
 * 与赛项 Python 端 nle_cloud.py 接口一致:
 *   POST {base}/users/login            登录取 AccessToken
 *   GET  {base}/Devices                查询设备
 *   POST {base}/Devices/{id}/Cmds      下发执行器命令(0/1)
 *
 * 本应用据此控制工位上的照明灯(m_steady_green)与风扇(m_fan)。
 */
public class CloudClient {

    private final String baseUrl;
    private String token;
    private int deviceId = -1;

    public CloudClient(String baseUrl) {
        String url = (baseUrl == null ? "" : baseUrl).trim();
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        this.baseUrl = url;
    }

    /** 登录云服务系统, 成功返回 true */
    public boolean login(String account, String password) {
        try {
            JSONObject body = new JSONObject();
            body.put("Account", account);
            body.put("Password", password);
            body.put("IsRememberMe", true);
            String resp = httpPost("/users/login", body, null);
            JSONObject json = new JSONObject(resp);
            JSONObject obj = json.optJSONObject("ResultObj");
            if (obj != null) {
                String t = obj.optString("AccessToken", "");
                if (!t.isEmpty()) {
                    token = t;
                    return true;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    /** 查询设备并缓存第一个设备 ID */
    public int bindFirstDevice() {
        try {
            String resp = httpGet("/Devices?PageSize=100&PageIndex=1", token);
            JSONObject json = new JSONObject(resp);
            JSONObject obj = json.optJSONObject("ResultObj");
            org.json.JSONArray arr;
            if (obj != null && obj.has("PageSet")) {
                arr = obj.optJSONArray("PageSet");
            } else {
                arr = json.optJSONArray("ResultObj");
            }
            if (arr != null && arr.length() > 0) {
                deviceId = arr.getJSONObject(0).optInt("DeviceID");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return deviceId;
    }

    /** 向执行器(照明灯/风扇)下发命令: value=1开, 0关 */
    public boolean sendCommand(String apiTag, int value) {
        if (deviceId < 0) bindFirstDevice();
        if (deviceId < 0 || token == null) return false;
        try {
            JSONObject body = new JSONObject();
            body.put("apikey", token);
            body.put("apitag", apiTag);
            body.put("value", value);
            String resp = httpPost("/Devices/" + deviceId + "/Cmds", body, token);
            JSONObject json = new JSONObject(resp);
            int sc = json.optInt("StatusCode", -1);
            return sc == 1 || sc == 2;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    /* ---------------- HTTP 工具 ---------------- */
    private String httpGet(String path, String authToken) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        c.setRequestMethod("GET");
        c.setConnectTimeout(5000);
        c.setReadTimeout(5000);
        if (authToken != null) c.setRequestProperty("AccessToken", authToken);
        String s = readAll(c.getInputStream());
        c.disconnect();
        return s;
    }

    private String httpPost(String path, JSONObject body, String authToken) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        c.setRequestMethod("POST");
        c.setConnectTimeout(5000);
        c.setReadTimeout(5000);
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/json");
        if (authToken != null) c.setRequestProperty("AccessToken", authToken);
        OutputStream os = c.getOutputStream();
        os.write(body.toString().getBytes(StandardCharsets.UTF_8));
        os.flush();
        os.close();
        String s = readAll(c.getInputStream());
        c.disconnect();
        return s;
    }

    private String readAll(InputStream is) throws Exception {
        BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line);
        br.close();
        return sb.toString();
    }
}
