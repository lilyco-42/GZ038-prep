/******************************************************************************
 * 文件名 : main.c
 * 项目   : 2-3 智能设备开发（GZ038 第8套 模块二）—— LoRa 双机环境监控与远程灯控
 *
 * 功能需求（严格按赛题）:
 *   1. 两个 LoRa 模块 L(A)、L(B)，L(A) 插光照温湿度二合一模块。
 *   2. 上电/复位: L(A)、L(B) 的 LED1、LED2 均不亮。
 *   3. L(A) 液晶屏实时显示光照、温度、湿度。
 *   4. L(B) 液晶屏显示 LED1、LED2 状态。
 *   5. 按 L(A) Key2 -> 远程切换 L(B) LED1 亮/灭；L(B) 屏显示“开启”/“关闭”。
 *   6. 按 L(A) Key3 -> 远程切换 L(B) LED2 呼吸/熄灭；L(B) 屏显示“呼吸”/“关闭”。
 *
 * 说明: 本文件同时包含 L(A) 与 L(B) 两套主循环逻辑，编译时由 board.h 中的
 *       NODE_ROLE 宏选择；硬件适配函数（ADC/I2C/LCD/UART/LED/KEY）在下方以
 *       接口声明形式给出，实际工程由 bsp.c 按板子实现。
 ******************************************************************************/

#include "board.h"

#include <stdio.h>
#include <string.h>

/* ===================== 硬件适配层接口（由 bsp.c 实现） ===================== */
extern void     BSP_Init(void);                       /* 时钟/GPIO/ADC/I2C/LCD/UART 初始化 */
extern uint32_t BSP_GetTick(void);                    /* 系统滴答(ms) */

/* LED 控制 */
extern void     LED1_On(void);
extern void     LED1_Off(void);
extern void     LED2_On(void);
extern void     LED2_Off(void);
extern void     LED2_SetBreath(uint8_t level);       /* 呼吸灯亮度 0~100 */

/* 按键（仅 L(A)）: 按下返回 1 */
extern uint8_t  Key2_Pressed(void);
extern uint8_t  Key3_Pressed(void);

/* 环境量采集（仅 L(A)） */
extern uint16_t Light_ReadAdc(void);                 /* 光照 ADC 0~4095 */
extern void     SHT_Read(float *temp, float *hum);   /* 温湿度 */

/* LCD 显示 */
extern void     LCD_ShowEnv(uint16_t light, float temp, float hum);   /* L(A) */
extern void     LCD_ShowLedStatus(uint8_t led1On, uint8_t led2Breath);/* L(B) */

/* LoRa 串口收发 */
extern void     LoRa_Send(const char *buf, uint16_t len);
extern int16_t  LoRa_Recv(char *out, uint16_t outLen);   /* 返回读到的字节数 */

/* ===================== 全局状态 ===================== */
#if (NODE_ROLE == NODE_A)
/* ---------- L(A): 采集 + 按键远程控制 ---------- */
static uint8_t led1RemoteOn   = 0;   /* L(B) LED1 当前目标状态: 0灭 1亮 */
static uint8_t led2Breath     = 0;   /* L(B) LED2 当前目标状态: 0灭 1呼吸 */
static uint8_t key2Last       = 1;   /* 按键上次电平(默认上拉=1) */
static uint8_t key3Last       = 1;

/* 把 0/1 目标状态通过 LoRa 发给 L(B) */
static void Lora_SendCmd(const char *cmd, uint8_t val)
{
    char frame[FRAME_BUF_LEN];
    int len = 0;
    len = snprintf(frame, sizeof(frame), "%s%s,%d" FRAME_TAIL,
                   FRAME_HEAD, cmd, (int)val);
    LoRa_Send(frame, (uint16_t)len);
}

int main(void)
{
    uint16_t light = 0;
    float temp = 0.0f, hum = 0.0f;
    uint32_t lastEnvTick = 0;

    BSP_Init();

    /* 上电: L(A) 自身 LED1、LED2 均不亮 */
    LED1_Off();
    LED2_Off();

    while (1)
    {
        uint32_t now = BSP_GetTick();

        /* 1. 读光照温湿度并刷新 L(A) 液晶屏 */
        light = Light_ReadAdc();
        SHT_Read(&temp, &hum);
        LCD_ShowEnv(light, temp, hum);

        /* 2. 周期(1s)把环境量上报给 L(B)（也可经 LoRa 网关上云） */
        if ((now - lastEnvTick) >= ENV_REPORT_MS)
        {
            lastEnvTick = now;
            char frame[FRAME_BUF_LEN];
            int len = snprintf(frame, sizeof(frame),
                               "%sENV,%u,%.1f,%.1f" FRAME_TAIL,
                               FRAME_HEAD, (unsigned)light, temp, hum);
            LoRa_Send(frame, (uint16_t)len);
        }

        /* 3. 按键扫描（下降沿触发，每 KEY_SCAN_MS 一次） */
        {
            static uint32_t keyTick = 0;
            if ((now - keyTick) >= KEY_SCAN_MS)
            {
                keyTick = now;
                uint8_t k2 = Key2_Pressed();   /* 按下=1 */
                uint8_t k3 = Key3_Pressed();

                /* Key2: 按下瞬间翻转 L(B) LED1 */
                if (k2 && !key2Last)
                {
                    led1RemoteOn = !led1RemoteOn;
                    Lora_SendCmd("LED1", led1RemoteOn);
                }
                /* Key3: 按下瞬间翻转 L(B) LED2 */
                if (k3 && !key3Last)
                {
                    led2Breath = !led2Breath;
                    Lora_SendCmd("LED2", led2Breath);
                }
                key2Last = k2;
                key3Last = k3;
            }
        }
    }
}

#else
/* ---------- L(B): 接收命令 + 本地 LED 呼吸灯 + 状态显示 ---------- */
static uint8_t led1On      = 0;   /* LED1 目标: 0灭 1亮 */
static uint8_t led2Breath  = 0;   /* LED2 目标: 0灭 1呼吸 */
static int16_t breathLevel = 0;
static int8_t  breathDir   = 1;   /* 1 上升, -1 下降 */
static uint32_t lastBreathTick = 0;
static char rxLine[FRAME_BUF_LEN];
static uint16_t rxLen = 0;

/* 解析一帧: $LA,LED1,1* / $LA,LED2,0* / $LA,ENV,...* */
static void ParseFrame(const char *line)
{
    char cmd[16] = {0};
    int val = 0;
    /* sscanf: 命令名 + 第一个数值 */
    if (sscanf(line, "$LA,%15[^,],%d", cmd, &val) == 2)
    {
        if (strcmp(cmd, "LED1") == 0)
        {
            led1On = (val != 0) ? 1 : 0;
        }
        else if (strcmp(cmd, "LED2") == 0)
        {
            led2Breath = (val != 0) ? 1 : 0;
            breathLevel = 0;
            breathDir = 1;
        }
        /* ENV 帧为 L(A) 上报，L(B) 不处理其环境量显示 */
    }
}

int main(void)
{
    BSP_Init();

    /* 上电: L(B) 的 LED1、LED2 均不亮 */
    LED1_Off();
    LED2_Off();
    led1On = 0;
    led2Breath = 0;

    /* 上电液晶屏显示一次初始状态 */
    LCD_ShowLedStatus(led1On, led2Breath);

    while (1)
    {
        uint32_t now = BSP_GetTick();

        /* 1. 接收 LoRa 数据，按帧尾 *\\r\\n 组帧后解析 */
        int16_t n = LoRa_Recv(rxLine + rxLen,
                              (uint16_t)(sizeof(rxLine) - rxLen - 1));
        if (n > 0)
        {
            rxLen += (uint16_t)n;
            rxLine[rxLen] = '\0';
            char *tail = strstr(rxLine, FRAME_TAIL);
            if (tail != NULL)
            {
                *tail = '\0';
                ParseFrame(rxLine);
                /* 剩余数据搬移到缓冲区头 */
                uint16_t consumed = (uint16_t)(tail - rxLine) + 4;
                memmove(rxLine, rxLine + consumed,
                        rxLen - consumed);
                rxLen = rxLen - consumed;
                rxLine[rxLen] = '\0';
                LCD_ShowLedStatus(led1On, led2Breath);
            }
            if (rxLen >= sizeof(rxLine) - 1) rxLen = 0;   /* 防溢出 */
        }

        /* 2. 本地输出 LED1 */
        if (led1On) LED1_On(); else LED1_Off();

        /* 3. 本地输出 LED2: 呼吸 或 灭 */
        if (led2Breath)
        {
            if ((now - lastBreathTick) >= BREATH_STEP_MS)
            {
                lastBreathTick = now;
                breathLevel += breathDir * 2;
                if (breathLevel >= BREATH_LEVEL_MAX)
                {
                    breathLevel = BREATH_LEVEL_MAX;
                    breathDir = -1;
                }
                else if (breathLevel <= 0)
                {
                    breathLevel = 0;
                    breathDir = 1;
                }
                LED2_SetBreath((uint8_t)breathLevel);
            }
        }
        else
        {
            LED2_Off();
        }
    }
}
#endif /* NODE_ROLE */
