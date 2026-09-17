/******************************************************************************
 * 文件名 : bsp.c
 * 项目   : 2-2 串口通讯系统开发（ZigBee 蓝色节点盒）
 * 说明   : 硬件适配层参考实现（以节点盒常见 STM32 + HAL 库为蓝本）。
 *          若节点盒为其它内核，仅需按同名函数重写底层寄存器操作即可，
 *          main.c 的协议逻辑无需改动。
 *
 * 关键串口配置：57600 波特率，8 数据位，无校验，1 停止位（8N1）。
 ******************************************************************************/
#include "main.h"

/* ---- 若使用 STM32 HAL，取消下面注释并在工程中加入 HAL 库 ----
#include "stm32f1xx_hal.h"

UART_HandleTypeDef huart1;          /* 节点盒与 USB 转串口相连的串口 */
static uint8_t s_rxByte;            /* 单次接收缓存 */

/* LED 引脚（按实际修改，示例：LED1=PB0, LED2=PB1） */
void LED_Write(GPIO_PORT port, GPIO_PIN pin, uint8_t on)
{
    if (port == LED1_PORT && pin == LED1_PIN)
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
    else if (port == LED2_PORT && pin == LED2_PIN)
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

void BSP_GPIO_Init(void)
{
    __HAL_RCC_GPIOB_CLK_ENABLE();
    GPIO_InitTypeDef g = {0};
    g.Pin   = GPIO_PIN_0 | GPIO_PIN_1;
    g.Mode  = GPIO_MODE_OUTPUT_PP;
    g.Pull  = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOB, &g);
}

void BSP_UART_Init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /* PA9 = TX, PA10 = RX */
    GPIO_InitTypeDef g = {0};
    g.Pin   = GPIO_PIN_9;
    g.Mode  = GPIO_MODE_AF_PP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &g);
    g.Pin  = GPIO_PIN_10;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOA, &g);

    huart1.Instance        = USART1;
    huart1.Init.BaudRate   = 57600;     /* 波特率 57600 */
    huart1.Init.WordLength = UART_WORDLENGTH_8B;  /* 8 数据位 */
    huart1.Init.StopBits   = UART_STOPBITS_1;     /* 1 停止位 */
    huart1.Init.Parity     = UART_PARITY_NONE;    /* 无校验 */
    huart1.Init.Mode       = UART_MODE_TX_RX;
    HAL_UART_Init(&huart1);

    /* 使能接收中断，开始接收第一个字节 */
    HAL_UART_Receive_IT(&huart1, &s_rxByte, 1);

    /* 配置 USART1 中断优先级并使能（NVIC） */
    HAL_NVIC_SetPriority(USART1_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
}

void BSP_UART_Send(const uint8_t *buf, uint16_t len)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)buf, len, 100);
}

/* USART1 中断服务函数：收到一字节回调，再继续收下一字节 */
void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        UART_RxCallback(s_rxByte);          /* 交给 main.c 的协议层 */
        HAL_UART_Receive_IT(&huart1, &s_rxByte, 1);
    }
}
------------------------------------------------------------
（若不使用 HAL，可在此处用标准库/寄存器方式实现同名函数，接口一致。）
------------------------------------------------------------ */

/* ---- 未接入真实芯片时的空实现（保证本文件可单独编译查看） ---- */
#ifndef USE_HAL_STUB
void LED_Write(GPIO_PORT port, GPIO_PIN pin, uint8_t on) { (void)port; (void)pin; (void)on; }
void BSP_GPIO_Init(void) {}
void BSP_UART_Init(void) {}
void BSP_UART_Send(const uint8_t *buf, uint16_t len) { (void)buf; (void)len; }
#endif
