/**************************************************************************
 * 文件名: main_A.c   (板 A 主控)
 * 说  明: GZ038 第6套 子任务2-2 设备无线通讯功能开发 —— 板 A
 * 平  台: CC2530 黑色 ZigBee 板(标签 "A")，作为无线发送方
 *
 * 赛题要求回顾:
 *   1) 短按板A的 SW1 -> 通过 ZigBee 通知板B，板B 的 RS232 数据值自动加一
 *      (板B 随后输出 FA NN FB, NN 从 00 起每次 +1);
 *   2) 长按板A的 SW1 不松开 -> LED1 亮、LED2 灭;
 *   3) 松开 SW1 -> LED1、LED2 都常亮;
 *   4) 板A、板B 通过 ZigBee 无线通讯，板B 用 RS232 接工作站 COM1 验证。
 *
 * 说明: 无线发送函数 Wireless_SendCmd() 在 Z-Stack 工程中对应
 *       AF_DataRequest() 发送簇 0x0123 / 端点 10，数据 CMD_INC。
 **************************************************************************/
#include <ioCC2530.h>
#include "board.h"
#include "protocol.h"

/* 1ms 节拍 */
static volatile unsigned long g_ms = 0;
void Timer1_Init(void);
static void Led1_On(void){ LED1 = 0; }   /* 低电平点亮 */
static void Led1_Off(void){ LED1 = 1; }
static void Led2_On(void){ LED2 = 0; }
static void Led2_Off(void){ LED2 = 1; }
static void Leds_AllOn(void){ Led1_On(); Led2_On(); }

/* Z-Stack 无线发送: 向板B发送"数据值加一"命令 */
extern void Wireless_SendCmd(unsigned char cmd);

/* 按键状态 */
static unsigned long tDown = 0;     /* 按下时刻 */
static unsigned char longFired = 0; /* 本次按下是否已触发过长亮状态 */
static unsigned char lastKey = KEY_UP;

void Timer1_ISR(void) __interrupt T1_VECTOR
{
  T1CTL &= ~0x01;
  g_ms++;
}

static void Timer1_Init(void)
{
  T1CTL = 0x0D;
  T1CCTL0 = 0x44;
  T1CC0 = 1000;
  T1IE = 1;
  EA = 1;
}

static void Port_Init(void)
{
  P1DIR |= 0x03;          /* LED1=P1.0 LED2=P1.1 输出 */
  P1SEL &= ~0x03;
  P0DIR &= ~0x02;         /* SW1=P0.1 输入 */
  P0INP &= ~0x02;
  P2INP &= ~0x20;         /* 上拉 */
}

/**************************************************************************
 * 主循环: 非阻塞处理 SW1 长按/短按
 **************************************************************************/
void main(void)
{
  unsigned char raw;
  Port_Init();
  Timer1_Init();
  Leds_AllOn();           /* 上电: 两灯都常亮 */

  while (1) {
    raw = SW1;

    if (raw == KEY_DOWN && lastKey == KEY_UP) {
      /* 刚按下 */
      tDown = g_ms;
      longFired = 0;
    }
    else if (raw == KEY_DOWN) {
      /* 按住中: 达到长按阈值 -> LED1亮 LED2灭(只触发一次) */
      if (!longFired && (g_ms - tDown >= LONG_PRESS_MS)) {
        longFired = 1;
        Led1_On();
        Led2_Off();
      }
    }
    else if (raw == KEY_UP && lastKey == KEY_DOWN) {
      /* 刚松开 */
      if (longFired) {
        /* 长按松开 -> 两灯都常亮 */
        Leds_AllOn();
      } else {
        /* 短按 -> 无线通知板B数据值加一; 同时保持两灯常亮 */
        Wireless_SendCmd(CMD_INC);
        Leds_AllOn();
      }
    }

    lastKey = raw;
  }
}
