/******************************************************************************
 * 文件名 : bsp.c
 * 项目   : 2-3 智能设备开发（LoRa 节点 + 光照传感器 + LCD 液晶屏）
 * 说明   : 硬件适配层参考实现。各函数按节点板实际接线/驱动改写，
 *          main.c 的业务逻辑（采集->显示->阈值->上报）不变。
 *
 * 接线/外设占位（按实际节点板修改）:
 *   光照传感器 AO  -> ADC 输入引脚（如 PA1/ADC1_IN1）
 *   LED1           -> GPIO 推挽输出（上电常亮）
 *   LED2           -> GPIO 推挽输出（阈值控制）
 *   LCD 液晶屏     -> I2C 或并行接口（如 1602/OLED）
 *   LoRa 模块      -> UART（如 USART2），与 LoRa 网关通讯
 ******************************************************************************/
#include "main.h"
#include <stdio.h>

/* ---- 上电状态记录 ---- */
static volatile uint32_t s_tickMs = 0;

uint32_t BSP_GetTick(void) { return s_tickMs; }   /* 由 SysTick 累加 */

/* ---- 外设初始化 ---- */
void BSP_Init(void)
{
    /* TODO(按板卡): RCC/GPIO/ADC(连续转换)/UART(LoRa,9600)/LCD(I2C) 初始化 */
    /* 示例(HAL):
       ADC1 初始化，12 位分辨率，扫描光照通道；
       USART2 初始化 9600 8N1 接 LoRa 模块；
       LCD_Init() 初始化液晶屏；
       LED1/LED2 配为推挽输出。 */
}

/* ---- 读光照 ADC：返回 0~4095 ---- */
uint16_t Light_ReadAdc(void)
{
    /* TODO(按板卡): 启动 ADC 转换并读取结果。
       return HAL_ADC_GetValue(&hadc1); */
    return 0;
}

/* ---- 液晶屏显示光照值 ----
 * 显示效果示意（第一行）:  Light: 1234
 *                      （第二行）  LED2: ON / OFF
 */
void LCD_ShowLight(uint16_t light, uint8_t led2On)
{
    char line[24];
    snprintf(line, sizeof(line), "Light: %u   ", (unsigned)light);
    /* TODO(按屏驱动): LCD_SetCursor(0,0); LCD_Puts(line); */
    snprintf(line, sizeof(line), "LED2: %s    ", led2On ? "ON " : "OFF");
    /* TODO(按屏驱动): LCD_SetCursor(0,1); LCD_Puts(line); */
}

/* ---- LoRa 上报光照值 ---- */
void LoRa_SendLight(uint16_t light)
{
    /* TODO(按 LoRa 模块协议): 组帧并经 UART 发送，例如：
       uint8_t frame[6] = {0xAA, 0x01,
                           (light >> 8) & 0xFF, light & 0xFF,
                           0x0D, 0x0A};
       HAL_UART_Transmit(&huart2, frame, 6, 100); */
    (void)light;
}

/* ---- LED 控制 ---- */
void LED1_On(void)  { /* TODO: GPIO 置位 */ }
void LED2_On(void)  { /* TODO: GPIO 置位 */ }
void LED2_Off(void) { /* TODO: GPIO 复位 */ }

/* ---- SysTick 中断 ----
void SysTick_Handler(void) { s_tickMs++; } */
