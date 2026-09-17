package com.env.newland.envmonitor;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * TCP 收到原始行的解析器。
 * 支持常见格式（大小写不敏感，允许中英文冒号 / 等号），例如：
 *   T:25.5 H:60.2 L:120 P:1
 *   T=25.5,H=60.2,L=120,P=1
 *   温度:25.5 湿度:60 光照:120 人体:1
 * 字段标记可配置（默认 T/温度、H/湿度/湿、L/光照/光、P/人体/人/PIR）。
 * 返回 Map 键：temp / humidity / light / human。
 */
public class DataParser {

    public static String[] MARKERS_TEMP = { "T", "\u6e29\u5ea6" };
    public static String[] MARKERS_HUM = { "H", "\u6e7f\u5ea6", "\u6e7f" };
    public static String[] MARKERS_LIGHT = { "L", "\u5149\u7167", "\u5149" };
    public static String[] MARKERS_HUMAN = { "P", "\u4eba\u4f53", "\u4eba", "PIR" };

    private static final Pattern NUMBER_PATTERN = Pattern.compile("[-+]?\\d+(\\.\\d+)?");

    private DataParser() {
    }

    public static Map<String, Double> parse(String line) {
        Map<String, Double> result = new HashMap<String, Double>();
        if (line == null) {
            return result;
        }
        Map<String, String> tokens = tokenize(line);
        Double temp = findValue(tokens, MARKERS_TEMP);
        Double hum = findValue(tokens, MARKERS_HUM);
        Double light = findValue(tokens, MARKERS_LIGHT);
        Double human = findValue(tokens, MARKERS_HUMAN);
        if (temp != null) {
            result.put("temp", temp);
        }
        if (hum != null) {
            result.put("humidity", hum);
        }
        if (light != null) {
            result.put("light", light);
        }
        if (human != null) {
            result.put("human", human);
        }
        return result;
    }

    /** 把一行切分为 “键=值” 单元，分隔符支持空格、逗号、分号、Tab、中文逗号分号。 */
    private static Map<String, String> tokenize(String line) {
        Map<String, String> result = new HashMap<String, String>();
        String[] parts = line.split("[\\s,;，；、\\t]+");
        for (String part : parts) {
            if (part == null || part.length() == 0) {
                continue;
            }
            int idx = -1;
            int a = part.indexOf(':');
            int b = part.indexOf('\uff1a'); // 中文冒号 ：
            int c = part.indexOf('=');
            if (a >= 0 && (idx < 0 || a < idx)) idx = a;
            if (b >= 0 && (idx < 0 || b < idx)) idx = b;
            if (c >= 0 && (idx < 0 || c < idx)) idx = c;
            if (idx > 0) {
                String k = part.substring(0, idx).trim();
                String v = part.substring(idx + 1).trim();
                if (k.length() > 0 && v.length() > 0) {
                    result.put(k, v);
                }
            }
        }
        return result;
    }

    /** 从键值对中按标记列表找值；精确匹配优先，其次前缀匹配。 */
    private static Double findValue(Map<String, String> tokens, String[] markers) {
        String bestKey = null;
        int bestScore = 0;
        for (String key : tokens.keySet()) {
            String k = key.trim();
            if (k.length() == 0) {
                continue;
            }
            String ku = k.toUpperCase(Locale.US);
            for (String marker : markers) {
                String m = marker.trim();
                if (m.length() == 0) {
                    continue;
                }
                String mu = m.toUpperCase(Locale.US);
                int score = 0;
                if (ku.equals(mu)) {
                    score = 3;
                } else if (ku.startsWith(mu)) {
                    score = 2;
                } else if (mu.length() >= 2 && ku.contains(mu)) {
                    score = 1;
                }
                if (score > bestScore) {
                    bestScore = score;
                    bestKey = key;
                }
            }
        }
        if (bestKey == null) {
            return null;
        }
        return parseNumber(tokens.get(bestKey));
    }

    /** 提取字符串中第一个十进制数字（忽略 °C、%RH 等单位后缀）。 */
    private static Double parseNumber(String raw) {
        if (raw == null) {
            return null;
        }
        Matcher m = NUMBER_PATTERN.matcher(raw.trim());
        if (m.find()) {
            try {
                return Double.parseDouble(m.group());
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }
}