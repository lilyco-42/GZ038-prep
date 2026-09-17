package com.newland.product;

import java.util.Arrays;
import java.util.List;

/**
 * 中距离一体机(UHF RFID)读头封装。
 *
 * 真机接入: 把官方 le_hardware_v1.jar 拷到 app/libs, 按其 RfidConnector /
 *   GenericConnector.readSingleEpc() 读取标签 EPC。本类已按该接口留好调用点,
 *   无硬件时自动回退为"模拟轮询"(依次轮播三个商品标签), 便于在终端上演示。
 */
public class RfidReader {

    private final List<String> simulateTags = Arrays.asList(
            "E28011600000000000000001",
            "E28011600000000000000002",
            "E28011600000000000000003");
    private int idx = 0;
    private boolean hasHardware = false;   // 真机就绪后置 true
    // private GenericConnector connector; // 真机: 来自 le_hardware_v1.jar

    public RfidReader() {
        try {
            // 真机初始化示例(需 le_hardware_v1.jar):
            //   DataBus bus = DataBusFactory.newSerialDataBus("/dev/ttyS1", 115200);
            //   connector = new GenericConnector(bus);
            // hasHardware = true;
        } catch (Throwable t) {
            hasHardware = false;
        }
    }

    /** 阻塞最多 ~200ms 返回一个 EPC, 无读到返回 null */
    public String readOne() {
        if (hasHardware) {
            // 真机: return connector.readSingleEpc().getEpc();
            return null;
        }
        // 模拟: 每 2 秒轮播一张标签
        try { Thread.sleep(2000); } catch (InterruptedException ignored) {}
        String tag = simulateTags.get(idx % simulateTags.size());
        idx++;
        return tag;
    }

    public void close() {
        // 真机: connector.close();
    }
}
