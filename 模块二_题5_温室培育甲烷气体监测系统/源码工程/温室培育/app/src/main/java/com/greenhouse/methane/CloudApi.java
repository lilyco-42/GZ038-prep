package com.greenhouse.methane;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * 物联网云服务系统（NLECloud / 新大陆云平台）RESTful 简易客户端。
 *
 * 接口：
 *   1. POST {base}/users/login            登录，返回 AccessToken
 *   2. GET  {base}/Devices                模糊查询设备
 *   3. GET  {base}/Devices/Datas?devIds=.. 批量查询设备传感器最新数据
 *   4. POST {base}/Devices/{id}/Cmds       向执行器(风扇)下发开关指令
 *
 * 除登录外，请求头需携带 AccessToken。
 * 本类全部为同步阻塞方法，务必在子线程调用。
 *
 * 说明：由原 Kotlin 版 CloudApi.kt 直译而来，业务逻辑保持一致。
 */
public class CloudApi {

    private String baseUrl;
    private String token;

    public CloudApi(String baseUrl) {
        this.baseUrl = (baseUrl == null ? "" : baseUrl).trim();
        if (this.baseUrl.endsWith("/")) {
            this.baseUrl = this.baseUrl.substring(0, this.baseUrl.length() - 1);
        }
        this.token = null;
    }

    public String getToken() {
        return token;
    }

    public void setBase(String url) {
        this.baseUrl = (url == null ? "" : url).trim();
        while (this.baseUrl.endsWith("/")) {
            this.baseUrl = this.baseUrl.substring(0, this.baseUrl.length() - 1);
        }
        this.token = null;
    }

    /** 登录。成功返回 true，并保存 token。 */
    public boolean login(String account, String password) {
        try {
            JSONObject payload = new JSONObject();
            payload.put("Account", account);
            payload.put("Password", password);
            payload.put("IsRememberMe", true);
            HttpURLConnection conn = openPost(baseUrl + "/users/login", null, payload.toString());
            try {
                String body = readStream(conn.getInputStream());
                JSONObject json = new JSONObject(body);
                JSONObject obj = json.optJSONObject("ResultObj");
                if (obj == null) return false;
                String t = obj.optString("AccessToken", "");
                if (t != null && !t.isEmpty()) {
                    token = t;
                    return true;
                }
                return false;
            } finally {
                conn.disconnect();
            }
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    /** 查询账号下所有设备，取第一个网关设备的 DeviceID。 */
    public int queryFirstDeviceId() {
        try {
            HttpURLConnection conn = openGet(baseUrl + "/Devices?PageSize=100&PageIndex=1");
            try {
                String body = readStream(conn.getInputStream());
                JSONObject json = new JSONObject(body);
                JSONObject obj = json.optJSONObject("ResultObj");
                JSONArray set = obj == null ? null : obj.optJSONArray("PageSet");
                if (set != null && set.length() > 0) {
                    return set.getJSONObject(0).optInt("DeviceID", 0);
                }
                return 0;
            } finally {
                conn.disconnect();
            }
        } catch (Exception e) {
            return -1;
        }
    }

    /** 读取指定传感器标识(ApiTag)的最新值。找到返回数值，找不到或失败返回 null。 */
    public Double fetchSensorValue(int devId, String apiTag) {
        if (devId <= 0) return null;
        try {
            HttpURLConnection conn = openGet(baseUrl + "/Devices/Datas?devIds=" + devId);
            try {
                String body = readStream(conn.getInputStream());
                JSONObject json = new JSONObject(body);
                JSONArray arr = json.optJSONArray("ResultObj");
                if (arr == null) return null;
                Double value = null;
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject dev = arr.getJSONObject(i);
                    JSONArray datas = dev.optJSONArray("Datas");
                    if (datas == null) continue;
                    for (int j = 0; j < datas.length(); j++) {
                        JSONObject s = datas.getJSONObject(j);
                        String tag = s.optString("ApiTag", "");
                        if (tag.equalsIgnoreCase(apiTag)) {
                            double v = s.optDouble("Value", Double.NaN);
                            if (!Double.isNaN(v)) value = v;
                        }
                    }
                }
                return value;
            } finally {
                conn.disconnect();
            }
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    /** 向执行器下发指令（开关风扇）。value: 1=开, 0=关。返回 true 表示云平台受理成功。 */
    public boolean sendCommand(int devId, String apiTag, int value) {
        if (devId <= 0) return false;
        try {
            JSONObject payload = new JSONObject();
            payload.put("apikey", token == null ? "" : token);
            payload.put("apitag", apiTag);
            payload.put("value", value);
            HttpURLConnection conn = openPost(baseUrl + "/Devices/" + devId + "/Cmds", token, payload.toString());
            try {
                String body = readStream(conn.getInputStream());
                JSONObject json = new JSONObject(body);
                int sc = json.optInt("StatusCode", -1);
                return sc == 1 || sc == 2;
            } finally {
                conn.disconnect();
            }
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    // ---------------- 底层 HTTP 工具 ---------------- //

    private HttpURLConnection openGet(String urlStr) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(8000);
        if (token != null && !token.isEmpty()) {
            conn.setRequestProperty("AccessToken", token);
        }
        return conn;
    }

    private HttpURLConnection openPost(String urlStr, String withToken, String body) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(8000);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json");
        if (withToken != null && !withToken.isEmpty()) {
            conn.setRequestProperty("AccessToken", withToken);
        }
        OutputStream os = conn.getOutputStream();
        os.write(body.getBytes("UTF-8"));
        os.flush();
        os.close();
        return conn;
    }

    private String readStream(InputStream stream) throws Exception {
        StringBuilder sb = new StringBuilder();
        BufferedReader reader = new BufferedReader(new InputStreamReader(stream, "UTF-8"));
        String line = reader.readLine();
        while (line != null) {
            sb.append(line);
            line = reader.readLine();
        }
        reader.close();
        return sb.toString();
    }
}
