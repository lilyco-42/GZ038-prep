#ifndef __BOARD_H__
#define __BOARD_H__
/**************************************************************************
 * 文件名: board.h
 * 说  明: GZ038 第9套 子任务2-3 NB-IoT 智能设备开发(环境监控灯)
 *        NB-IoT 板引脚/底层接口定义。在赛题提供的未完成工程上补全 main;
 *        传感器/LCD/USB/LED2 的底层驱动由原工程实现, 本文件只声明接口。
 *        如实际引脚不同, 改对应底层函数即可, main.c 无需改动。
 **************************************************************************/
#include <stdint.h>

/* ---------- LED2: 温控指示灯(高/低电平有效由底层屏蔽) ---------- */
void Led2_On(void);        /* LED2 点亮(温度<28℃) */
void Led2_Off(void);       /* LED2 熄灭(温度>=28℃) */

/* ---------- 温湿度光照传感器: 读取原始值(浮点, 多位小数) ---------- */
/* 温度单位 ℃, 湿度单位 %RH, 光照单位 lux(本任务不显示, 保留接口) */
float Sensor_ReadRawTemp(void);
float Sensor_ReadRawHum(void);
float Sensor_ReadRawLux(void);

/* ---------- 液晶屏: 按行显示字符串 (1/2/3 行) ---------- */
/* 赛题: 第2行=温度实时值+单位, 第3行=湿度实时值+单位 */
void LCD_ShowLine(uint8_t line, const char *text);

/* ---------- USB 串口(虚拟串口, 波特率 115200) ---------- */
void Usb_SendString(const char *s);   /* 发送字符串(以'\0'结尾) */

/* ---------- 系统节拍(非阻塞延时用) ---------- */
void     Board_Init(void);
void     SysTick_Start(void);
void     SysTick_IncMs(void);
uint32_t SysTick_GetMs(void);

#endif /* __BOARD_H__ */
