/****************************************************************************
 * hal_board.h  蓝色 ZigBee 节点盒 板级引脚定义（子任务2-2）
 *--------------------------------------------------------------------------*
 * 本文件集中管理 LED1 / LED2 / SW1 的引脚映射。
 * 若实际工位节点盒丝印与默认值不同，只改这里即可，main.c 无需改动。
 ****************************************************************************/
#ifndef __HAL_BOARD_H__
#define __HAL_BOARD_H__

#include <ioCC2530.h>

/* ---- 引脚映射（按新大陆蓝色 ZigBee 节点盒默认接线） ---- */
#define HAL_LED1_PORT_DIR      P1DIR
#define HAL_LED1_BIT           0
#define HAL_LED2_PORT_DIR      P1DIR
#define HAL_LED2_BIT           1

#define HAL_SW1_PORT_SEL       P0SEL
#define HAL_SW1_PORT_DIR       P0DIR
#define HAL_SW1_PORT_INP       P0INP
#define HAL_SW1_BIT            1

/* ---- 电平极性 ----
 * LED：共阳，输出 0 点亮。
 * SW1：内部上拉，按下接地，读到 0。
 */
#define HAL_LED_ON_LEVEL       0
#define HAL_LED_OFF_LEVEL      1
#define HAL_KEY_PRESS_LEVEL    0

#endif /* __HAL_BOARD_H__ */
