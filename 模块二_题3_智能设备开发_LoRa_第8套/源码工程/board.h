/******************************************************************************
 * 文件名 : board.h
 * 项目   : 2-3 智能设备开发（GZ038 第8套 模块二）—— LoRa 双机环境监控与远程灯控
 * 平台   : CC2530 / STM32 风格 LoRa 节点（主控 MCU + 光照温湿度二合一 + LCD + LoRa 模块）
 *
 * 任务说明:
 *   两个 LoRa 模块分别命名为 L(A) 和 L(B)，L(A) 上插光照温湿度二合一模块。
 *   - 上电/复位: L(A)、L(B) 的 LED1、LED2 均不亮。
 *   - L(A) 液晶屏实时显示光照、温度、湿度。
 *   - L(B) 液晶屏显示 LED1、LED2 的状态。
 *   - 按 L(A) 的 Key2: 远程切换 L(B) 的 LED1 亮/灭；L(B) 屏显示“开启”/“关闭”。
 *   - 按 L(A) 的 Key3: 远程切换 L(B) 的 LED2 呼吸/熄灭；L(B) 屏显示“呼吸”/“关闭”。
 *
 * 本文件集中管理: 节点角色选择、引脚定义、LoRa 串口协议参数。
 * 编译时通过宏 NODE_ROLE 选择烧录到 L(A) 还是 L(B):
 *   - 烧 L(A): 在工程选项中定义  -DNODE_ROLE=NODE_A
 *   - 烧 L(B): 在工程选项中定义  -DNODE_ROLE=NODE_B
 ******************************************************************************/
#ifndef __BOARD_H__
#define __BOARD_H__

#include <stdint.h>

/* ===================== 节点角色选择 ===================== */
#define NODE_A      1     /* L(A): 采集节点，插光照温湿度二合一，带 Key2/Key3 */
#define NODE_B      2     /* L(B): 被控节点，带 LED1/LED2 与状态液晶屏       */

/* 若工程未指定 NODE_ROLE，默认编译为 L(A) */
#ifndef NODE_ROLE
#define NODE_ROLE   NODE_A
#endif

/* ===================== 引脚定义（按实际原理图修改） ===================== */
/* LED 引脚（推挽输出，高电平点亮） */
#define LED1_PORT        PA
#define LED1_PIN         1
#define LED2_PORT        PA
#define LED2_PIN         2

/* 按键引脚（带上拉，按下为低电平）—— 仅 L(A) 使用 */
#define KEY2_PORT        PC
#define KEY2_PIN         0
#define KEY3_PORT        PC
#define KEY3_PIN         1

/* 光照温湿度二合一模块：光照走 ADC，温湿度走 I2C（SHT30 风格） */
#define LIGHT_ADC_CH     1            /* ADC 通道 1，12 位分辨率 0~4095 */
#define SHT_SCL_PORT     PB
#define SHT_SCL_PIN      6
#define SHT_SDA_PORT     PB
#define SHT_SDA_PIN      7

/* LCD 液晶屏（1602 / OLED 风格，I2C 或并行） */
#define LCD_I2C_ADDR     0x3E

/* LoRa 模块串口（USART2，9600 8N1） */
#define LORA_UART        2
#define LORA_BAUD        9600

/* ===================== LoRa 通讯协议 ===================== */
/* 自定义应用帧（ASCII 文本帧，便于调试）:
 *   帧格式:  $LA,<CMD>,<VAL>*\r\n
 *   CMD = LED1: 控制 L(B) 的 LED1     VAL = 1(亮) / 0(灭)
 *   CMD = LED2: 控制 L(B) 的 LED2     VAL = 1(呼吸) / 0(灭)
 *   CMD = ENV : L(A) 周期上报环境量    VAL = 光照,温度,湿度（逗号分隔）
 */
#define FRAME_HEAD       "$LA,"
#define FRAME_TAIL       "*\r\n"
#define FRAME_BUF_LEN    64

/* ===================== 系统周期参数 ===================== */
#define TICK_1MS         1            /* 系统时基 1ms */
#define ENV_REPORT_MS    1000         /* L(A) 环境量上报周期 1s */
#define KEY_SCAN_MS      20           /* 按键扫描周期 */
#define BREATH_STEP_MS   20          /* 呼吸灯 PWM 步进周期 */
#define BREATH_LEVEL_MAX 100         /* 呼吸灯亮度等级 0~100 */

#endif /* __BOARD_H__ */
