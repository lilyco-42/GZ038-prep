/*****************************************************************************
 * 文件名称 : main.h (板B —— 接收端)
 * 所属任务 : GZ038 第4套 模块二 子任务2-2
 ****************************************************************************/
#ifndef __MAIN_H__
#define __MAIN_H__

typedef unsigned char  uint8;
typedef unsigned short uint16;
typedef unsigned int   uint32;

void SystemClock_Init(void);
void Delay_ms(uint16 ms);

/* 接风扇的继电器 (P1_1) */
void Relay_Fan_Init(void);          /* 初始化, 默认关闭 */
void Relay_Fan_Write(uint8 on);     /* 1=吸合(风扇转) 0=断开(风扇停) */

/* 板B 状态指示灯 (P1_0) */
void Led_Init(void);
void Led_Write(uint8 on);           /* 1=亮 0=灭 */

/* UART0 (连接 ZigBee 透传模块), 开接收中断 */
void Uart0_Init(uint32 baud);
void OnUartRxByte(uint8 byte);     /* 收到 1 字节时调用, 内部按协议组帧 */

#endif /* __MAIN_H__ */
