package com.cinema.newland.cinema;

import java.util.HashSet;
import java.util.Set;

/**
 * RFID 票箱数据 + 读卡器抽象（2-4 智能电影院系统）。
 *
 * 中距离一体机读取到 RFID 标签后：
 *  - 售卖界面：激活电影票（把标签号加入“已售”集合，持久化到 SharedPreferences）。
 *  - 首界面：循环读卡，命中“已售”集合 -> 开闸，3 秒后关闸并跳主界面。
 *
 * 真实读卡器通过 TCP/串口与中距离一体机通讯；这里把读卡结果抽象为
 * 一个接口 readTag()，现场按厂商 SDK 实现即可，界面逻辑不变。
 */
public class RfidTicketStore {

    public static final String PREFS = "cinema_tickets";
    public static final String KEY_SOLD = "sold_tags";

    /** 判断某标签是否已售（已激活电影票）。 */
    public static boolean isSold(android.content.Context ctx, String tag) {
        if (tag == null) return false;
        return ctx.getSharedPreferences(PREFS, 0)
                .getStringSet(KEY_SOLD, new HashSet<String>())
                .contains(tag.trim().toUpperCase());
    }

    /** 激活电影票：把标签号加入已售集合。 */
    public static void markSold(android.content.Context ctx, String tag) {
        if (tag == null) return;
        Set<String> set = new java.util.HashSet<>(
                ctx.getSharedPreferences(PREFS, 0).getStringSet(KEY_SOLD, new HashSet<String>()));
        set.add(tag.trim().toUpperCase());
        ctx.getSharedPreferences(PREFS, 0).edit().putStringSet(KEY_SOLD, set).apply();
    }

    /**
     * 读取一次 RFID 标签 EPC。
     * 真实设备：通过中距离一体机 TCP/串口发送读标签指令并解析。
     * 返回标签字符串；无标签返回 null。
     */
    public static String readTag() {
        // TODO(现场): 通过 TcpSerialClient 连接中距离一体机读标签口，
        // 发送读 EPC 指令，解析返回帧中的 EPC 并返回。
        return null;
    }
}
