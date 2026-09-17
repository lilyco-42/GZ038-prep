#ifndef __PROTOCOL_H__
#define __PROTOCOL_H__
/**************************************************************************
 * 文件名: protocol.h
 * 说  明: GZ038 第6套 子任务2-2 板A<->板B 无线/串口 通讯协议定义
 *
 * 赛题要求: 板B 经 RS232 向外输出格式: FA 00 FB
 *   FA = 数据头(0xFA)
 *   00 = 数据值(按 SW1 次数自动加一, 0x00..0xFF 循环)
 *   FB = 数据尾(0xFB)
 *
 * 板A 按 SW1(短按) -> 无线通知板B"数据值加一" -> 板B 通过 RS232 输出新帧。
 **************************************************************************/

/* 串口帧字节常量 */
#define FRAME_HEAD   0xFA
#define FRAME_TAIL   0xFB

/* 无线应用簇/端点约定(便于在 Z-Stack 中对齐两端) */
#define WIRELESS_EP          10
#define WIRELESS_CLUSTERID   0x0123
/* 无线命令字: 板A->板B 请求"数据值加一" */
#define CMD_INC             0x01

/* RS232 串口参数 */
#define UART_BAUD           9600   /* 板B 接工作站 COM1, 9600 8N1 */

#endif /* __PROTOCOL_H__ */
