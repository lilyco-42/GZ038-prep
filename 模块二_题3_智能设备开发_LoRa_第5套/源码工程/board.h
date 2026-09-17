#ifndef __BOARD_H__
#define __BOARD_H__
/**************************************************************************
 * 文件名: board.h
 * 说  明: GZ038 第5套 子任务2-3 LoRa 智能设备开发 —— LoRa 节点板引脚定义
 *        本工程在赛题提供的"未完成工程"基础上补全 main 逻辑；
 *        LCD 驱动由原工程提供(这里只声明接口)。
 *        如工位引脚不同，仅改本文件。
 **************************************************************************/
#include <stdint.h>

/* ---------- LED1 / LED2: 推挽输出。1=亮 0=灭(按实际板可改) ---------- */
#define LED1_ON()    Led1_Write(1)
#define LED1_OFF()   Led1_Write(0)
#define LED2_ON()    Led2_Write(1)
#define LED2_OFF()   Led2_Write(0)

/* ---------- 按键 KEY2/KEY3/KEY4: 上拉输入，按下为低 ---------- */
#define KEY2_DOWN()  (Key2_Read() == 0)
#define KEY3_DOWN()  (Key3_Read() == 0)
#define KEY4_DOWN()  (Key4_Read() == 0)

/* ---------- 引脚读写接口(由 board.c/原工程底层实现) ---------- */
void    Led1_Write(uint8_t on);
void    Led2_Write(uint8_t on);
uint8_t Key2_Read(void);
uint8_t Key3_Read(void);
uint8_t Key4_Read(void);

/* ---------- PWM 占空比(呼吸灯用): duty 0~100 ---------- */
void    Led1_SetDuty(uint8_t duty);
void    Led2_SetDuty(uint8_t duty);

/* ---------- LCD 接口(由原未完成工程提供) ---------- */
/* 显示主菜单，cursor 为当前 < 选中项 0/1/2 */
void    LCD_ShowMenu(uint8_t cursor);
/* 清屏 */
void    LCD_Clear(void);

/* ---------- 板级初始化 ---------- */
void    Board_Init(void);
/* 启动 1ms 系统节拍(在中断里调用 SysTick_IncMs()) */
void    SysTick_Start(void);
void    SysTick_IncMs(void);
uint32_t SysTick_GetMs(void);

#endif /* __BOARD_H__ */
