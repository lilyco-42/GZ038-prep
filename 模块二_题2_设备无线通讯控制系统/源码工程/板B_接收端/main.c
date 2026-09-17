/*****************************************************************************
 * 文件名称 : main.c (板B —— 无线通讯控制【接收端】)
 * 所属任务 : GZ038 第4套 模块二 子任务2-2 设备无线通讯控制系统
 * 功能描述 :
 *   本板为两块黑色 ZigBee 开发板中的【B 板】, 贴"板B"标签。
 *   板B 上接一个继电器, 继电器另一端连接风扇。
 *   板B 通过 ZigBee 无线链路(经 UART 透传)接收板A 发来的控制帧,
 *   校验通过后翻转继电器输出, 从而实现"板A 按一次 SW1, 板B 风扇启停一次"。
 *
 * 通讯协议(与板A 完全一致):
 *   帧头1  帧头2  命令字  校验和
 *   0xAA   0x55   CMD      SUM
 *   SUM = 0xAA + 0x55 + CMD, 低 8 位。CMD = 0x01 风扇翻转。
 *
 * 硬件约定:
 *   - 继电器(控制风扇)  : P1_1  (高电平=继电器吸合=风扇转; 低电平=停止)
 *   - ZigBee 模块串口   : UART0, 9600 8N1, 接收中断中组帧
 *   - 板B 状态指示灯    : P1_0  (跟随风扇状态: 转=亮, 停=灭)
 ****************************************************************************/

#include "main.h"

/* 协议常量, 与板A 保持一致 */
#define FRAME_HEAD1    0xAAu
#define FRAME_HEAD2    0x55u
#define CMD_FAN_TOGGLE 0x01u
#define FRAME_LEN      4u      /* 一帧固定 4 字节 */

/* 接收帧解析状态机状态 */
typedef enum {
    SYNC_HEAD1 = 0,     /* 等待帧头1 */
    SYNC_HEAD2,         /* 等待帧头2 */
    RECV_CMD,           /* 收命令字 */
    RECV_SUM            /* 收校验和 */
} ParseState;

static ParseState s_state = SYNC_HEAD1;
static uint8 s_cmd  = 0;
static uint8 s_fan_on = 0;     /* 风扇当前状态: 0=停 1=转 */

/*---------------------------------------------------------------------------
 * 继电器控制: 直接驱动接风扇的继电器输出
 *---------------------------------------------------------------------------*/
void Fan_Set(uint8 on)
{
    s_fan_on = on ? 1 : 0;
    Relay_Fan_Write(s_fan_on);         /* 写继电器引脚 */
    Led_Write(s_fan_on);              /* 板B 指示灯跟随风扇状态 */
}

void Fan_Toggle(void)
{
    Fan_Set((uint8)(!s_fan_on));       /* 翻转 */
}

/*---------------------------------------------------------------------------
 * 函数: void OnUartRxByte(uint8 byte)
 * 描述: UART0 接收中断中调用。按状态机组帧, 校验通过则执行风扇翻转。
 *---------------------------------------------------------------------------*/
void OnUartRxByte(uint8 byte)
{
    uint8 expect_sum;

    switch (s_state)
    {
        case SYNC_HEAD1:
            if (byte == FRAME_HEAD1) { s_state = SYNC_HEAD2; }
            break;

        case SYNC_HEAD2:
            if (byte == FRAME_HEAD2) { s_state = RECV_CMD; }
            else                     { s_state = SYNC_HEAD1; }  /* 重新同步 */
            break;

        case RECV_CMD:
            s_cmd = byte;
            s_state = RECV_SUM;
            break;

        case RECV_SUM:
            expect_sum = (uint8)(FRAME_HEAD1 + FRAME_HEAD2 + s_cmd);
            if (byte == expect_sum && s_cmd == CMD_FAN_TOGGLE)
            {
                Fan_Toggle();          /* 校验通过: 翻转风扇 */
            }
            s_state = SYNC_HEAD1;      /* 复位状态机, 准备下一帧 */
            break;

        default:
            s_state = SYNC_HEAD1;
            break;
    }
}

/*---------------------------------------------------------------------------
 * 函数: void BoardB_Init(void)
 * 描述: 板B 初始化。
 *---------------------------------------------------------------------------*/
void BoardB_Init(void)
{
    SystemClock_Init();
    Relay_Fan_Init();           /* 继电器(风扇)引脚, 默认关闭 */
    Led_Init();                 /* 板B 指示灯 */
    Uart0_Init(9600);           /* 与 ZigBee 模块相连的串口, 开接收中断 */
    Fan_Set(0);                 /* 上电风扇默认停止 */
}

/*---------------------------------------------------------------------------
 * 主函数
 *---------------------------------------------------------------------------*/
void main(void)
{
    BoardB_Init();

    while (1)
    {
        /* 接收与组帧在 UART 中断里完成, 主循环只需保持运行,
         * 也可在此处做心跳/看门狗喂狗等任务。 */
        Delay_ms(10);
    }
}
