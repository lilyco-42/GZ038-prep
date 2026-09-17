#ifndef __BOARD_H__
#define __BOARD_H__

/*============================================================================
 * board.h  LoRa 环境监控节点 板级支持包(BSP)头文件
 *----------------------------------------------------------------------------
 * 适用平台: 新大陆竞赛平台 LoRa 模块(STM32 + SX127x),
 *           外挂温湿度光照一体传感器模块。
 *
 * 硬件连线:
 *   LED2  -> PA_1   (低电平点亮, 光照<100lux 时点亮)
 *   SW2   -> PB_0   (按下为低电平; 按下=ASCII 发送, 松开=HEX 发送)
 *   温湿度 -> I2C1   (SHT30 类温湿度传感器, 地址 0x44)
 *   光照   -> ADC1_IN0 (光敏分压, 读电压后换算 lux)
 *   USB串口-> USART1 (USB 转串口连工作站, 波特率 115200)
 *==========================================================================*/

#include <stdint.h>

/*------------------------- 引脚(按模块丝印修改) ---------------------------*/
#define LED2_ON()        (gpio_led2 = 0)
#define LED2_OFF()       (gpio_led2 = 1)
extern volatile uint8_t gpio_led2;

#define SW2_DOWN()       (gpio_sw2 == 0)   /* 按下为低 */
extern volatile uint8_t gpio_sw2;

/*------------------------- 串口参数 ----------------------------------------*/
#define UART_BAUDRATE    115200

/*------------------------- 光照阈值 ---------------------------------------*/
#define LIGHT_THRESHOLD_LUX   100.0f       /* 光照<100lux 点亮 LED2 */

/*============================================================================
 * BSP 接口
 *==========================================================================*/
void    Board_Init(void);                          /* 时钟/IO/I2C/ADC/UART 初始化 */
float   Sensor_ReadTemperature(void);             /* 返回 ℃, 内部取整显示 */
float   Sensor_ReadHumidity(void);                 /* 返回 %RH */
float   Sensor_ReadLightVoltage(void);            /* 返回光敏电压 V */
void    UART_SendBytes(const uint8_t *buf, uint32_t len);  /* 串口发送原始字节 */
void    Delay_ms(uint32_t ms);

#endif /* __BOARD_H__ */
