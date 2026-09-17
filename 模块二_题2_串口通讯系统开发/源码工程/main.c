/******************************************************************************
 * 文件名 : main.c
 * 项目   : 2-2 串口通讯系统开发（GZ038 第3套 模块二）
 * 平台   : ZigBee 蓝色节点盒（STM32 主控，UART 串口模式）
 * 功能   : 通过 USB 转串口线与工作站通讯，57600 8N1，
 *          工作站下发单字节指令 0xE1/0xE2/0xF1/0xF2 控制板上 LED1/LED2，
 *          并按赛题要求回带回车换行(\r\n)字符串。
 *
 * 串口参数 : 波特率 57600，数据位 8，无校验，停止位 1（57600 8N1）
 *
 * 上电行为 : LED1 点亮 3 秒后熄灭，LED2 熄灭。
 *
 * 协议字节表（工作站 -> 节点盒）:
 *   0xE1 : LED1 点亮，回 "The LED1 is Open! \r\n"
 *   0xE2 : LED1 熄灭，回 "The LED1 is Closed! \r\n"
 *   0xF1 : LED2 点亮，回 "The LED2 is Open! \r\n"
 *   0xF2 : LED2 熄灭，回 "The LED2 is Closed! \r\n"
 *   其它 : 不响应（保持当前 LED 状态）
 *
 * 说明   : 本文件以节点盒常见 STM32 为蓝本编写，GPIO/UART 宏已集中定义，
 *          移植到具体芯片时仅需修改 “硬件适配层” 中的宏与初始化函数。
 ******************************************************************************/

#include "main.h"

/* ============================ 硬件适配层（按实际节点盒修改） ============================ */
/* LED1 / LED2 引脚宏。高电平点亮则写 ON=1 / OFF=0，低电平点亮则反之。 */
#define LED1_ON()        LED_Write(LED1_PORT, LED1_PIN, 1)
#define LED1_OFF()       LED_Write(LED1_PORT, LED1_PIN, 0)
#define LED2_ON()        LED_Write(LED2_PORT, LED2_PIN, 1)
#define LED2_OFF()       LED_Write(LED2_PORT, LED2_PIN, 0)

/* 上电后 LED1 点亮的时长（毫秒） */
#define LED1_BOOT_ON_MS  3000U

/* 指令字节定义（严格按赛题） */
#define CMD_LED1_OPEN    0xE1
#define CMD_LED1_CLOSE   0xE2
#define CMD_LED2_OPEN    0xF1
#define CMD_LED2_CLOSE   0xF2

/* 回包字符串（注意：感叹号后保留一个空格，末尾带回车换行 \r\n，严格按赛题） */
#define RSP_LED1_OPEN    "The LED1 is Open! \r\n"
#define RSP_LED1_CLOSE   "The LED1 is Closed! \r\n"
#define RSP_LED2_OPEN    "The LED2 is Open! \r\n"
#define RSP_LED2_CLOSE   "The LED2 is Closed! \r\n"

/* 全局：当前收到的串口指令字节（在 UART 接收中断中置位，主循环处理） */
static volatile uint8_t  g_rxByte    = 0;     /* 收到的字节 */
static volatile uint8_t  g_rxFlag    = 0;     /* 1=有新字节待处理 */
static volatile uint32_t g_tickMs    = 0;     /* 系统毫秒计数（由 SysTick 提供） */

/* LED 状态记录，便于回显 */
static uint8_t g_led1State = 0;
static uint8_t g_led2State = 0;

/* ============================ 对外底层接口（由 BSP 实现） ============================ */
extern void     BSP_GPIO_Init(void);                 /* 初始化 LED1/LED2 为推挽输出 */
extern void     BSP_UART_Init(void);                 /* 初始化 UART：57600 8N1，开接收中断 */
extern void     BSP_UART_Send(const uint8_t *buf, uint16_t len); /* 阻塞发送 */
extern void     LED_Write(GPIO_PORT port, GPIO_PIN pin, uint8_t on); /* 写 LED 电平 */
extern uint32_t BSP_GetTick(void);                   /* 返回系统毫秒数 */

/* ============================ 工具函数 ============================ */
static void UART_SendString(const char *s)
{
    BSP_UART_Send((const uint8_t *)s, (uint16_t)strlen(s));
}

/* ============================ 指令处理 ============================ */
static void ProcessCommand(uint8_t cmd)
{
    switch (cmd)
    {
        case CMD_LED1_OPEN:                 /* 0xE1 -> LED1 亮 */
            g_led1State = 1;
            LED1_ON();
            UART_SendString(RSP_LED1_OPEN);
            break;

        case CMD_LED1_CLOSE:                /* 0xE2 -> LED1 灭 */
            g_led1State = 0;
            LED1_OFF();
            UART_SendString(RSP_LED1_CLOSE);
            break;

        case CMD_LED2_OPEN:                /* 0xF1 -> LED2 亮 */
            g_led2State = 1;
            LED2_ON();
            UART_SendString(RSP_LED2_OPEN);
            break;

        case CMD_LED2_CLOSE:               /* 0xF2 -> LED2 灭 */
            g_led2State = 0;
            LED2_OFF();
            UART_SendString(RSP_LED2_CLOSE);
            break;

        default:                            /* 其它字节：不动作，不回包 */
            break;
    }
}

/* ============================ UART 接收中断回调 ============================
 * 在 UART RX 中断服务函数中调用：取出收到的字节并置位标志。
 * 主循环检测到标志后再处理，避免在中断里做耗时回包。 */
void UART_RxCallback(uint8_t byte)
{
    g_rxByte = byte;
    g_rxFlag = 1;
}

/* ============================ 主函数 ============================ */
int main(void)
{
    /* 1. 初始化硬件：GPIO（LED）+ UART（57600 8N1，接收中断使能） */
    BSP_GPIO_Init();
    BSP_UART_Init();

    /* 2. 上电默认状态：LED2 熄灭 */
    LED2_OFF();
    g_led2State = 0;

    /* 3. 上电行为：LED1 点亮 3 秒后熄灭 */
    LED1_ON();
    g_led1State = 1;
    {
        uint32_t start = BSP_GetTick();
        while ((BSP_GetTick() - start) < LED1_BOOT_ON_MS)
        {
            /* 上电 3 秒内仍可响应串口指令 */
            if (g_rxFlag)
            {
                g_rxFlag = 0;
                ProcessCommand(g_rxByte);
            }
        }
    }
    LED1_OFF();
    g_led1State = 0;

    /* 4. 主循环：持续处理串口指令 */
    while (1)
    {
        if (g_rxFlag)
        {
            g_rxFlag = 0;
            ProcessCommand(g_rxByte);
        }
        /* 此处可加低功耗 / 其它业务，指令处理不依赖延时。 */
    }
}

/* ============================ SysTick 中断：维护毫秒节拍 ============================ */
void SysTick_Handler(void)
{
    g_tickMs++;
}

uint32_t BSP_GetTick(void)
{
    return g_tickMs;
}
