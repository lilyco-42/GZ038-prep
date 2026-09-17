/**************************************************************************
 * 文件名: main.c
 * 说  明: GZ038 第9套 子任务2-3 智能设备的开发(NB-IoT 板)
 *        环境监控灯功能: 温湿度光照采集 + LCD 显示 + LED2 温控 + 串口上报
 * 平  台: NB-IoT 节点板(在赛题提供的未完成工程上补全), main.c + board.h
 *
 * 赛题要求回顾:
 *   1) 液晶屏第2行显示温度实时采集值+单位, 第3行显示湿度实时采集值+单位;
 *   2) 温度 < 28℃  -> LED2 点亮;  温度 >= 28℃ -> LED2 熄灭;
 *   3) NB-IoT 板放智慧盒, USB 线连工作站(波特率 115200);
 *   4) 每 1 秒通过 USB 向工作站上报三行:
 *        第1行: 温湿度"原始采集值"(带6位小数)+单位;
 *        第2行: 温湿度"显示值"(与LCD一致)+单位;
 *        第3行: LED灯当前状态。
 **************************************************************************/
#include "board.h"
#include <stdio.h>
#include <string.h>

#define TEMP_ALARM_C    28.0f    /* 温控阈值: 低于此温度 LED2 亮, 高于等于则灭 */
#define REPORT_PERIOD_MS 1000    /* USB 上报周期 1 秒 */

/* 最近一次采集到的数据 */
static float    g_rawTemp = 0.0f;   /* 温度原始值(传感器ADC换算, 多位小数) */
static float    g_rawHum  = 0.0f;    /* 湿度原始值 */
static uint8_t  g_led2On  = 0;      /* LED2 当前状态 1=亮 0=灭 */
static uint32_t g_lastReport = 0;

/* ------------------------------------------------------------------ */
/* 由原始值求"显示值": LCD 上展示的温度/湿度, 保留 1 位小数            */
/* ------------------------------------------------------------------ */
static float DispTemp(float raw)
{
  int t = (int)(raw * 10.0f + (raw >= 0 ? 0.5f : -0.5f));
  return t / 10.0f;
}
static float DispHum(float raw)
{
  int t = (int)(raw * 10.0f + (raw >= 0 ? 0.5f : -0.5f));
  return t / 10.0f;
}

/* ------------------------------------------------------------------ */
/* 根据当前温度刷新 LED2: <28℃ 亮, >=28℃ 灭                          */
/* ------------------------------------------------------------------ */
static void UpdateLedByTemp(void)
{
  uint8_t want = (g_rawTemp < TEMP_ALARM_C) ? 1 : 0;
  if (want != g_led2On) {
    g_led2On = want;
    if (want) Led2_On(); else Led2_Off();
  }
}

/* ------------------------------------------------------------------ */
/* 刷新 LCD: 第1行标题, 第2行温度, 第3行湿度                          */
/* ------------------------------------------------------------------ */
static void UpdateLcd(void)
{
  char line[24];
  float dt = DispTemp(g_rawTemp);
  float dh = DispHum(g_rawHum);

  LCD_ShowLine(1, "环境监控");
  /* 第2行: 温度显示值+单位 */
  sprintf(line, "温度:%.1f C", dt);
  LCD_ShowLine(2, line);
  /* 第3行: 湿度显示值+单位 */
  sprintf(line, "湿度:%.1f %%", dh);
  LCD_ShowLine(3, line);
}

/* ------------------------------------------------------------------ */
/* 每 1 秒通过 USB(115200)上报三行                                    */
/* ------------------------------------------------------------------ */
static void SendReport(void)
{
  char buf[96];
  float dt = DispTemp(g_rawTemp);
  float dh = DispHum(g_rawHum);

  /* 第1行: 原始采集值, 6 位小数 + 单位 */
  sprintf(buf, "温度=%.6f C, 湿度=%.6f %%RH\r\n", g_rawTemp, g_rawHum);
  Usb_SendString(buf);

  /* 第2行: 显示值(与LCD一致) + 单位 */
  sprintf(buf, "温度=%.1f C, 湿度=%.1f %%RH\r\n", dt, dh);
  Usb_SendString(buf);

  /* 第3行: LED2 当前状态 */
  sprintf(buf, "LED2状态:%s\r\n", g_led2On ? "开" : "关");
  Usb_SendString(buf);
}

int main(void)
{
  Board_Init();          /* 传感器/LCD/USB(115200)/LED2 底层初始化 */
  SysTick_Start();

  g_lastReport = SysTick_GetMs();

  while (1) {
    uint32_t now = SysTick_GetMs();

    /* 1. 采集温湿度原始值(光照本任务未要求显示, 一并读取保留接口) */
    g_rawTemp = Sensor_ReadRawTemp();
    g_rawHum  = Sensor_ReadRawHum();

    /* 2. 按温度阈值刷新 LED2, 刷新 LCD */
    UpdateLedByTemp();
    UpdateLcd();

    /* 3. 每 1 秒上报一次(非阻塞) */
    if ((uint32_t)(now - g_lastReport) >= REPORT_PERIOD_MS) {
      g_lastReport = now;
      SendReport();
    }
  }
}
