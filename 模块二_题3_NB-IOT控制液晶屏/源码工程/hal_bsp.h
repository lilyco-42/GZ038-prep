/****************************************************************************
 * hal_bsp.h  NB-IoT 节点盒 板级支持包声明（子任务2-3）
 *--------------------------------------------------------------------------*
 * 把 LCD / 按键 / 串口 / LED2 的板级驱动统一抽象。
 * 真实工程中在 bsp.c 里实现这些函数即可，main.c 业务逻辑与板子无关。
 ****************************************************************************/
#ifndef __HAL_BSP_H__
#define __HAL_BSP_H__

#include <stdint.h>
#include <stdbool.h>

/* LCD 驱动 */
void HAL_Lcd_Init(void);
void HAL_Lcd_Clear(void);
void HAL_Lcd_ShowStr(uint8_t col, uint8_t row, const char *s);

/* LED2：true 点亮 */
void HAL_Led2_Set(bool on);

/* 串口：发送 / 轮询读取一个字节 */
void     HAL_Uart_Send(const uint8_t *data, uint16_t n);
uint8_t  HAL_Uart_PollByte(bool *got);   /* 无字节时 *got=false */

/* 按键扫描：返回键码 1~4，无键返回 0 */
uint8_t  HAL_Key_Scan(void);

/* 延时 */
void     HAL_DelayMs(uint16_t ms);

/* 串口接收中断里直接调用：把收到的字节交给协议解析。
   推荐做法：在 UART RX 中断服务函数中调用 OnUartByte(byte)。 */
void     OnUartByte(uint8_t b);

#endif /* __HAL_BSP_H__ */
