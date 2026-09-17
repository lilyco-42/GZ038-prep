package com.newland.roomtemp;

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
 *   POST {base}/users/login            登录取 AccessToken
 *   GET  {base}/Devices                查询设备
 *   GET  {base}/Devices/Datas?devIds=  批量取传感器最新值
 *
 * 本应用据此读取工位温湿度传感器: m_temp(温度) / m_hum(湿度)。
 */
public class CloudClient {

    private final String baseUrl;
    private String token;
    private int deviceId = -1;

    public CloudClient(String baseUrl) {
        this.baseUrl = (baseUrl == null ? "" : baseUrl).trim();
        if (this.baseUrl.endsWith("/")) {
            this.baseUrl = this.baseUrl.substring(0, this.baseUrl.length() - 1);
        }
    }

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
                if (!t.isEmpty()) { token = t; return true; }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    public int bindFirstDevice() {
        try {
            String resp = httpGet("/Devices?PageSize=100&PageIndex=1", token);
            JSONObject json = new JSONObject(resp);
            JSONObject obj = json.optJSONObject("ResultObj");
            org.json.JSONArray arr;
            if (obj != null && obj.has("PageSet")) arr = obj.optJSONArray("PageSet");
            else arr = json.optJSONArray("ResultObj");
            if (arr != null && arr.length() > 0) {
                deviceId = arr.getJSONObject(0).optInt("DeviceID");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return deviceId;
    }

    /** 读取某传感器(ApiTag)最新值, 读不到返回 null */
    public Double readSensor(String apiTag) {
        if (deviceId < 0) bindFirstDevice();
        if (deviceId < 0) return null;
        try {
            String resp = httpGet("/Devices/Datas?devIds=" + deviceId, token);
            JSONObject json = new JSONObject(resp);
            org.json.JSONArray arr = json.optJSONArray("ResultObj");
            if (arr == null) {
                JSONObject obj = json.optJSONObject("ResultObj");
                if (obj != null) arr = obj.optJSONArray("Datas");
            }
            if (arr != null) {
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject d = arr.getJSONObject(i);
                    if (apiTag.equalsIgnoreCase(d.optString("ApiTag", ""))) {
                        return d.optDouble("Value", Double.NaN);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

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
