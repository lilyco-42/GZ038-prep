/**************************************************************************
 * 文件名: main.c
 * 说  明: GZ038 第9套 子任务2-2 CC2530 单片机开发 —— 串口通讯系统
 *        (通过串口控制黑色 ZigBee 模块板上 D4/D3/D6/D5 四颗 LED)
 * 平  台: CC2530 黑色 ZigBee 核心板 (IAR EW8051, main.c + board.h)
 *
 * 硬件连接:
 *   黑色 ZigBee(CC2530)模块 --DB9公头转端子线--> 串口服务器 COM3
 *   串口服务器工作在 TCP Server/Client 模式, 把网口 TCP 数据透明
 *   转发到 COM3 串口; 工作站电脑用 NetAssist 以 TCP 方式连串口服务器,
 *   即可向本模块收发指令。本侧只需按 8N1 9600bps 做裸串口收发。
 *
 * 赛题要求回顾:
 *   1) 上电即运行: D5 点亮 2 秒后熄灭, D4/D3/D6 保持熄灭;
 *   2) 灯位绑定(指令字节 0~15 的二进制, 1=亮 0=灭):
 *        位序  1   2   3   4
 *        灯名  D4  D3  D6  D5
 *        即指令字节 b3->D4, b2->D3, b1->D6, b0->D5
 *        例: 0x02 = 0010 -> D6 亮, 其余灭;
 *   3) 上位机下发指令帧(共4字节):
 *        FE  01  cmd  FF
 *        FE=起始符  01=功能码(控制LED)  cmd=0x00~0x0F  FF=结束符
 *   4) 本模块返回状态帧(共9字节):
 *        FE  01  04  sD4  sD3  sD6  sD5  crcH  crcL
 *        04=状态字节数(4)  sXx: 00=关 01=开
 *        crcH/crcL = CRC-16/Modbus(对 FE 01 04 sD4 sD3 sD6 sD5 共7字节计算)
 *                    高字节在前。赛题示例 FE 01 04 00 00 01 00 -> 4E F5。
 **************************************************************************/
#include <ioCC2530.h>
#include "board.h"

/* ============================ 全局变量 ================================= */
static volatile unsigned short g_tickMs = 0;      /* 1ms 节拍计数器 */

/* 四颗灯的"逻辑"状态: 1=亮 0=灭 (与返回帧 sXx 一致) */
static unsigned char g_stD4 = 0;
static unsigned char g_stD3 = 0;
static unsigned char g_stD6 = 0;
static unsigned char g_stD5 = 0;

/* 上电 2 秒提示灯状态机: 0=未开始 1=D5亮计时中 2=提示结束 */
static unsigned char  g_bootPhase  = 0;
static unsigned short g_bootTimer  = 0;

/* 串口接收帧解析状态机 */
static unsigned char g_rxStep = 0;   /* 0=等FE 1=等功能码01 2=收cmd 3=等FF */
static unsigned char g_rxCmd = 0;

/* ============================ 函数声明 ================================ */
static void  Port_Init(void);
static void  Uart0_Init(unsigned char baud);
static void  Timer1_Init(void);
static void  Leds_Apply(void);
static void  Led_SetByCmd(unsigned char cmd);
static void  Uart0_SendByte(unsigned char b);
static void  Uart0_SendBuf(unsigned char *p, unsigned char n);
static unsigned short Crc16_Modbus(unsigned char *p, unsigned char n);
static void  Send_StatusFrame(void);

/**************************************************************************
 * 端口初始化: LED 为推挽输出
 **************************************************************************/
static void Port_Init(void)
{
  /* P1.0~P1.3 接 D4/D3/D6/D5 -> 全部推挽输出 */
  P1DIR |= 0x0F;
  P1SEL &= ~0x0F;
}

/**************************************************************************
 * UART0 初始化: 8 位数据, 无校验, 1 停止位, 收发中断
 *   TX=P0.3, RX=P0.2 (CC2530 黑色 ZigBee 模块默认 UART0 引脚)
 **************************************************************************/
static void Uart0_Init(unsigned char baud)
{
  /* 引脚复用: P0.2/P0.3 为外设功能 */
  P0SEL |= 0x0C;
  P0DIR &= ~0x04;          /* P0.2(RX) 输入 */
  P0DIR |=  0x08;          /* P0.3(TX) 输出 */

  /* UART0 切换到备用位置1: P0.2/P0.3 */
  PERCFG &= ~0x01;
  /* 外设优先级: UART0 优先 */
  P2DIR  &= ~0xC0;

  /* 波特率寄存器: 由 board.h 给出(32MHz 下 9600bps) */
  U0BAUD = baud;
  U0GCR  = BAUD_U0GCR;

  U0UCR = 0x80;            /* 清除缓冲 */
  U0CSR = 0x80;            /* UART 模式, 接收器使能 */

  U0IEN |= 0x02;           /* 允许 RX 中断 */
  P2IEN |= 0x01;           /* 允许 UART0 中断 */
  IEN2  |= 0x01;
  EA = 1;
}

/**************************************************************************
 * Timer1 初始化: 1ms 定时中断, 提供系统节拍
 *   32MHz / 32分频 = 1us/tick, 计数 1000 = 1ms
 **************************************************************************/
static void Timer1_Init(void)
{
  T1CTL = 0x0D;            /* /32, 模模式 */
  T1CCTL0 = 0x44;
  T1CC0 = 1000;
  T1IE = 1;
  EA = 1;
}

void Timer1_ISR(void) __interrupt T1_VECTOR
{
  T1CTL &= ~0x01;
  if (g_tickMs < 0xFFFF) g_tickMs++;
}

/**************************************************************************
 * 把 g_stXx 逻辑状态刷到引脚 (板灯低电平点亮: 亮->输出0, 灭->输出1)
 **************************************************************************/
static void Leds_Apply(void)
{
  D4 = g_stD4 ? 0 : 1;
  D3 = g_stD3 ? 0 : 1;
  D6 = g_stD6 ? 0 : 1;
  D5 = g_stD5 ? 0 : 1;
}

/**************************************************************************
 * 按指令字节(0~15)更新四颗灯逻辑状态并输出
 *   b3->D4  b2->D3  b1->D6  b0->D5
 **************************************************************************/
static void Led_SetByCmd(unsigned char cmd)
{
  if (cmd > 0x0F) cmd = 0x0F;
  g_stD4 = (cmd >> 3) & 0x01;
  g_stD3 = (cmd >> 2) & 0x01;
  g_stD6 = (cmd >> 1) & 0x01;
  g_stD5 = (cmd     ) & 0x01;
  Leds_Apply();
}

/**************************************************************************
 * UART0 发送一个字节
 **************************************************************************/
static void Uart0_SendByte(unsigned char b)
{
  U0DBUF = b;
  while (U0TXIF == 0) ;    /* 等发送完成 */
  U0TXIF = 0;
}

static void Uart0_SendBuf(unsigned char *p, unsigned char n)
{
  unsigned char i;
  for (i = 0; i < n; i++) Uart0_SendByte(p[i]);
}

/**************************************************************************
 * CRC-16/Modbus: init=0xFFFF, poly=0xA001(反射), 对 p[0..n-1] 计算
 *   结果低字节在后、高字节在前发送(与赛题"高字节在前"一致)
 **************************************************************************/
static unsigned short Crc16_Modbus(unsigned char *p, unsigned char n)
{
  unsigned short crc = 0xFFFF;
  unsigned char i, j;
  for (i = 0; i < n; i++) {
    crc ^= p[i];
    for (j = 0; j < 8; j++) {
      if (crc & 0x0001) crc = (crc >> 1) ^ 0xA001;
      else              crc >>= 1;
    }
  }
  return crc;
}

/**************************************************************************
 * 组装并发送状态返回帧:
 *   FE 01 04 sD4 sD3 sD6 sD5 crcH crcL
 **************************************************************************/
static void Send_StatusFrame(void)
{
  unsigned char buf[9];
  unsigned short crc;
  buf[0] = 0xFE;
  buf[1] = 0x01;
  buf[2] = 0x04;           /* 状态字节数 = 4 */
  buf[3] = g_stD4;
  buf[4] = g_stD3;
  buf[5] = g_stD6;
  buf[6] = g_stD5;
  crc = Crc16_Modbus(buf, 7);   /* 对前 7 字节计算 */
  buf[7] = (unsigned char)(crc >> 8);   /* 高字节在前 */
  buf[8] = (unsigned char)(crc & 0xFF);
  Uart0_SendBuf(buf, 9);
}

/**************************************************************************
 * UART0 RX 中断服务: 收一字节, 按 FE 01 cmd FF 解析指令帧
 **************************************************************************/
void UART0_ISR(void) __interrupt URX0_VECTOR
{
  unsigned char b;
  URX0IF = 0;                 /* 清中断标志 */
  b = U0DBUF;

  switch (g_rxStep) {
    case 0:                   /* 等起始符 FE */
      if (b == 0xFE) g_rxStep = 1;
      else           g_rxStep = 0;
      break;
    case 1:                   /* 等功能码 01 */
      if (b == 0x01) g_rxStep = 2;
      else           g_rxStep = 0;
      break;
    case 2:                   /* 收指令字节 cmd(0x00~0x0F) */
      g_rxCmd = b;
      g_rxStep = 3;
      break;
    case 3:                   /* 等结束符 FF */
      if (b == 0xFF) {
        /* 一帧收齐: 上电提示结束后才响应控制指令 */
        if (g_bootPhase == 2) {
          Led_SetByCmd(g_rxCmd);
        }
        Send_StatusFrame();   /* 无论何种状态都回当前4灯状态 */
      }
      g_rxStep = 0;
      break;
    default:
      g_rxStep = 0;
      break;
  }
}

/**************************************************************************
 * 主函数
 **************************************************************************/
void main(void)
{
  Port_Init();
  Uart0_Init(BAUD_9600);
  Timer1_Init();

  /* 上电提示: D5 亮 2 秒, D4/D3/D6 灭 */
  g_bootPhase = 1;
  g_stD4 = 0; g_stD3 = 0; g_stD6 = 0; g_stD5 = 1;
  Leds_Apply();
  g_bootTimer = g_tickMs;

  while (1) {
    /* 上电 2 秒提示计时(非阻塞) */
    if (g_bootPhase == 1) {
      if ((unsigned short)(g_tickMs - g_bootTimer) >= 2000) {
        g_bootPhase = 2;
        g_stD5 = 0;             /* D5 熄灭, 其余本就为 0 */
        Leds_Apply();
      }
    }
    /* 其余时间由串口中断驱动; 此处可进低功耗 */
  }
}
