/******************************************************************************
 * 文件名 : main.h
 * 项目   : 2-2 串口通讯系统开发（ZigBee 节点盒 UART 57600 8N1）
 * 说明   : 公共类型与硬件引脚定义。移植时按节点盒实际原理图修改。
 ******************************************************************************/
#ifndef __MAIN_H
#define __MAIN_H

#include <stdint.h>
#include <string.h>

/* ---- 引脚抽象：按节点盒原理图修改为实际 GPIO 端口/引脚 ---- */
typedef enum { LED1_PORT = 0, LED2_PORT = 1 } GPIO_PORT;   /* 仅示例占位，实际用 GPIOA/GPIOB... */
typedef enum { LED1_PIN  = 0, LED2_PIN  = 1 } GPIO_PIN;

/* ---- 函数声明见 main.c 与 bsp.c ---- */
#endif /* __MAIN_H */
