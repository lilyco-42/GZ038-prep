#ifndef __BOARD_H__
#define __BOARD_H__
/**************************************************************************
 * 文件名: board.h
 * 说  明: GZ038 第6套 子任务2-2 设备无线通讯功能开发
 *        两块黑色 ZigBee(CC2530)板 A、B 的共用引脚定义。
 *        A、B 建两个 IAR 工程，均引用本文件；分别编译下载 main_A.c / main_B.c。
 *        如工位引脚不同，仅改本文件。
 **************************************************************************/
#include <ioCC2530.h>

/* ---------- 板载 LED1 / LED2: 低电平点亮(0=亮,1=灭) ---------- */
#define LED1   P1_0
#define LED2   P1_1

/* ---------- 按键 SW1: 上拉输入，按下为低 ---------- */
#define SW1    P0_1
#define KEY_DOWN  0
#define KEY_UP    1

/* 长按判定阈值(ms) */
#define LONG_PRESS_MS   1000
/* 消抖时间(ms) */
#define DEBOUNCE_MS     20

#endif /* __BOARD_H__ */
