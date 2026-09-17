/**************************************************************************
 * 文件名: main_B.c   (板 B 接收方 + RS232 上报)
 * 说  明: GZ038 第6套 子任务2-2 设备无线通讯功能开发 —— 板 B
 * 平  台: CC2530 黑色 ZigBee 板(标签 "B")，用 RS232 接工作站 COM1
 *
 * 赛题要求回顾:
 *   1) 板B 通过 RS232 向外输出固定格式: FA NN FB
 *      (FA=数据头, NN=数据值, FB=数据尾)，初始 NN=00;
 *   2) 板A 短按 SW1 -> 无线通知板B -> 板B 数据值自动加一
 *      (依次输出 FA 01 FB, FA 02 FB, ...);
 *   3) 工作站串口调试助手(COM1,9600 8N1)可验证上述帧。
 *
 * 说明: 无线接收在 Z-Stack 中对应 AF 数据指示回调，
 *       收到 CMD_INC 后调用 OnWirelessCmd()。
 **************************************************************************/
#include <ioCC2530.h>
#include "board.h"
#include "protocol.h"

static unsigned char g_counter = 0;   /* 数据值, 0x00 起, 满 0xFF 回 0x00 */

/* ---------- UART0(RS232) 发送一个字节, 9600 8N1 ---------- */
static void Uart0_SendByte(unsigned char b)
{
  U0DBUF = b;
  while (U0TXIF == 0);   /* 等待发送完成 */
  U0TXIF = 0;
}

/* 发送一帧: FA NN FB */
static void Uart0_SendFrame(unsigned char val)
{
  Uart0_SendByte(FRAME_HEAD);   /* FA */
  Uart0_SendByte(val);          /* NN 数据值 */
  Uart0_SendByte(FRAME_TAIL);   /* FB */
}

/* ---------- UART0 初始化: 9600 8N1, P0.2=TX P0.3=RX ---------- */
static void Uart0_Init(void)
{
  PERCFG &= ~0x01;          /* UART0 备用位置1 */
  P0SEL  |= 0x0C;           /* P0.2/P0.3 外设功能 */
  U0CSR  |= 0x80;           /* UART 模式 */
  U0BAUD  = 59;             /* 32MHz -> 9600bps (59) */
  U0UCR |= 0x80;            /* 允许发送 */
}

/**************************************************************************
 * 无线收到板A命令后的处理(由 Z-Stack AF 接收回调调用)
 **************************************************************************/
void OnWirelessCmd(unsigned char cmd)
{
  if (cmd == CMD_INC) {
    g_counter++;                       /* 数据值自动加一 */
    Uart0_SendFrame(g_counter);        /* 经 RS232 输出 FA NN FB */
  }
}

void main(void)
{
  Uart0_Init();

  /* 上电先输出一帧初始值 FA 00 FB(赛题规定初始数据值为 00) */
  g_counter = 0;
  Uart0_SendFrame(g_counter);

  /* Z-Stack 协议栈启动后会自动完成组网; 收到无线 CMD_INC 时
     协议栈回调 OnWirelessCmd()。此处进入协议栈主循环(占位)。 */
  while (1) {
    /* 在纯 Z-Stack 工程中此循环为 OSAL_RunEventLoop();
       裸机演示版可在此空转，由接收中断驱动 OnWirelessCmd()。 */
  }
}
