/******************************************************************************
 * 文件名 : main.c
 * 项目   : 2-3 智能设备开发（GZ038 第3套 模块二）
 * 平台   : LoRa 节点（主控 MCU + 光照传感器模块 + LCD 液晶屏 + LoRa 模块）
 *
 * 功能需求（严格按赛题）:
 *   1. 设备上电后，板上 LED1 亮，LED2 灭。
 *   2. 液晶屏实时显示当前光照值。
 *   3. 当光照低于设定值（可用手遮住）时，板上 LED2 亮；
 *      高于该设定值（手拿开）时，LED2 灭。
 *   4. 通过 LoRa 模块周期性上报光照值。
 *
 * 说明 : 本工程以“提供的未完成工程”为骨架补全。ADC 读光照、LCD 刷屏、
 *        LoRa 发送均集中在硬件适配层，主循环只做“读值 -> 显示 -> 判断 -> 上报”。
 ******************************************************************************/

#include "main.h"

/* ============================ 参数配置 ============================ */
/* 光照低于此阈值 LED2 亮（手遮住光敏模块时光照下降）。
 * ADC 为 12 位(0~4095)，按实际传感器分压标定修改。 */
#define LIGHT_THRESHOLD    1000U

/* 主循环采样/刷屏/上报周期(ms) */
#define LOOP_PERIOD_MS     200U

/* ============================ 硬件适配层接口（由 bsp.c 实现） ============================ */
extern void    BSP_Init(void);                       /* 时钟/GPIO/ADC/LCD/LoRa 初始化 */
extern uint16_t Light_ReadAdc(void);                 /* 读光照传感器 ADC 原始值(0~4095) */
extern void    LCD_ShowLight(uint16_t light, uint8_t led2On); /* 液晶屏显示光照值 */
extern void    LoRa_SendLight(uint16_t light);       /* 通过 LoRa 上报光照值 */
extern void    LED1_On(void);
extern void    LED2_On(void);
extern void    LED2_Off(void);
extern uint32_t BSP_GetTick(void);

/* ============================ 主函数 ============================ */
int main(void)
{
    uint16_t light = 0;
    uint8_t  led2On = 0;

    /* 1. 初始化所有外设 */
    BSP_Init();

    /* 2. 上电固定状态：LED1 亮，LED2 灭 */
    LED1_On();
    LED2_Off();
    led2On = 0;

    /* 3. 主循环：实时采集 -> 显示 -> 阈值判断 -> LoRa 上报 */
    while (1)
    {
        /* 3.1 读光照传感器 ADC 原始值 */
        light = Light_ReadAdc();

        /* 3.2 阈值判断：低于阈值 LED2 亮，否则灭 */
        if (light < LIGHT_THRESHOLD)
        {
            if (led2On == 0) { LED2_On();  led2On = 1; }
        }
        else
        {
            if (led2On == 1) { LED2_Off(); led2On = 0; }
        }

        /* 3.3 液晶屏实时显示当前光照值（附带 LED2 状态） */
        LCD_ShowLight(light, led2On);

        /* 3.4 通过 LoRa 周期性上报光照值到网关/云 */
        LoRa_SendLight(light);

        /* 3.5 控制采样周期 */
        {
            uint32_t start = BSP_GetTick();
            while ((BSP_GetTick() - start) < LOOP_PERIOD_MS) { /* 等待 */ }
        }
    }
}
