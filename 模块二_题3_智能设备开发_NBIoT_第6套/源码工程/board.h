#ifndef __BOARD_H__
#define __BOARD_H__
/**************************************************************************
 * 文件名: board.h
 * 说  明: GZ038 第6套 子任务2-3 NB-IoT 智能设备开发 —— NB-IoT 板引脚定义
 *        在赛题提供的未完成工程上补全 main 逻辑; LCD/图片资源由原工程提供。
 **************************************************************************/
#include <stdint.h>

/* LED2 三档亮度: 0灭, 1微亮(PWM低占空), 2全亮(PWM满占空) */
#define LED2_LEVEL_OFF     0
#define LED2_LEVEL_DIM     1
#define LED2_LEVEL_FULL    2

/* 亮度占空比(0~100) */
#define DUTY_OFF           0
#define DUTY_DIM           15     /* 微亮 */
#define DUTY_FULL          100    /* 全亮 */

/* 按键: 上拉输入, 按下为低 */
#define KEY2_DOWN()        (Key2_Read() == 0)
#define KEY3_DOWN()        (Key3_Read() == 0)

/* 接口(底层由原工程实现) */
void    Led2_SetDuty(uint8_t duty);
uint8_t Key2_Read(void);
uint8_t Key3_Read(void);

/* LCD 三屏内容(由原工程图片资源提供, 这里只切换显示) */
void    LCD_ShowScreen(uint8_t idx);   /* 0/1/2 对应三屏 */
void    Board_Init(void);
void    SysTick_Start(void);
void    SysTick_IncMs(void);
uint32_t SysTick_GetMs(void);

#endif /* __BOARD_H__ */
