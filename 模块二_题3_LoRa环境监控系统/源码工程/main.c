/*============================================================================
 * main.c  子任务2-3 LoRa 环境监控系统
 *----------------------------------------------------------------------------
 * 硬件: 1 块 LoRa 模块 + 温湿度光照传感器模块
 *
 * 任务要求(逐条对应):
 *   [1] 采集温度/湿度/光照度并在板上 OLED 显示, 显示值不带小数。
 *   [2] 光照度换算公式:
 *         LightLux = pow(10, ( (1.78 - log10(33/voltage - 10)) / 0.6 ))
 *       其中 voltage 为光敏分压得到的电压(V)。
 *   [3] 光照 < 100 lux -> LoRa 板 LED2 亮; 否则 LED2 灭。
 *   [4] LoRa 模块 USB 连工作站, 串口波特率 115200; 网络调试工具默认 HEX。
 *   [5] 数据 ASCII 格式:  temperature:27|humidity:36|light:1210
 *       对应 HEX 格式即该字符串的原始字节:
 *         74 65 6D 70 65 72 61 74 75 72 65 3A 32 37 7C 68 75 6D 69 64
 *         69 74 79 3A 33 36 7C 6C 69 67 68 74 3A 31 32 31 30
 *   [6] 按住 SW2 -> 以 ASCII 方式发送; 松开 SW2 -> 恢复 HEX 方式发送。
 *
 * 说明:
 *   网络调试工具在 HEX 显示模式下看到的 "74 65 6D..." 正是字符串
 *   "temperature:..." 的 ASCII 字节; 切到 ASCII 显示模式即可看到可读文本。
 *   设备侧两种方式发送的负载字节完全一致, 区别在于:
 *     - HEX 方式(松开 SW2): 直接发送负载字节, 不加额外换行;
 *     - ASCII 方式(按住 SW2): 发送负载字节并附加 "\r\n", 方便人读。
 *==========================================================================*/
#include "board.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

/*------------------------- 环境数据结构体 ----------------------------------*/
typedef struct {
    int16_t temp;     /* 温度, 整数 ℃ */
    int16_t hum;      /* 湿度, 整数 %RH */
    int32_t light;    /* 光照, 整数 lux */
} EnvData;

/*============================================================================
 * 光照度换算(严格按题目公式)
 *   LightLux = 10 ^ ( (1.78 - log10(33/voltage - 10)) / 0.6 )
 *==========================================================================*/
static int32_t Calc_LightLux(float voltage)
{
    if (voltage <= 0.0f) {
        return 0;
    }
    double ratio = 33.0 / (double)voltage - 10.0;   /* 33/voltage - 10 */
    if (ratio <= 0.0) {
        return 0;
    }
    double lux = pow(10.0, (1.78 - log10(ratio)) / 0.6);
    if (lux < 0.0) lux = 0.0;
    return (int32_t)(lux + 0.5);                    /* 四舍五入取整 */
}

/*============================================================================
 * 采集一次环境数据
 *==========================================================================*/
static EnvData Env_Sample(void)
{
    EnvData d;
    float t = Sensor_ReadTemperature();
    float h = Sensor_ReadHumidity();
    float v = Sensor_ReadLightVoltage();

    d.temp  = (int16_t)(t + (t >= 0 ? 0.5f : -0.5f));   /* 取整, 不带小数 */
    d.hum   = (int16_t)(h + (h >= 0 ? 0.5f : -0.5f));
    d.light = Calc_LightLux(v);
    return d;
}

/*============================================================================
 * 组帧并通过串口发送
 *   mode = 0 : HEX 方式(松开 SW2) -> 发送负载字节, 不加换行
 *   mode = 1 : ASCII 方式(按住 SW2) -> 发送负载字节 + "\r\n"
 *==========================================================================*/
static void Env_Send(const EnvData *d, uint8_t ascii_mode)
{
    char frame[64];
    int len = snprintf(frame, sizeof(frame),
                       "temperature:%d|humidity:%d|light:%d",
                       (int)d->temp, (int)d->hum, (int)d->light);

    /* 先发负载字节(无论 HEX/ASCII 模式, 线上字节都与题目 HEX 示例一致) */
    UART_SendBytes((const uint8_t *)frame, (uint32_t)len);

    if (ascii_mode) {
        /* ASCII 显示模式下补回车换行, 方便网络调试工具逐行阅读 */
        static const uint8_t crlf[2] = { '\r', '\n' };
        UART_SendBytes(crlf, 2);
    }
}

/*============================================================================
 * 板上 OLED 显示(不带小数)
 *   在 bsp 中实现 OLED_ShowXxx; 这里只调用接口
 *==========================================================================*/
extern void OLED_ShowEnv(const EnvData *d);   /* bsp.c 中实现 */

/*============================================================================
 * 主函数
 *==========================================================================*/
int main(void)
{
    Board_Init();

    while (1) {
        EnvData d = Env_Sample();                 /* [1][2] 采集并换算 */

        /* [3] 光照 < 100 lux -> LED2 亮, 否则灭 */
        if (d.light < (int32_t)LIGHT_THRESHOLD_LUX) {
            LED2_ON();
        } else {
            LED2_OFF();
        }

        OLED_ShowEnv(&d);                         /* 显示整数值 */

        /* [5][6] 根据 SW2 状态选择发送方式 */
        uint8_t ascii_mode = SW2_DOWN() ? 1 : 0;   /* 按住=ASCII, 松开=HEX */
        Env_Send(&d, ascii_mode);

        Delay_ms(1000);                            /* 1 秒上报一次, 可调 */
    }
}
