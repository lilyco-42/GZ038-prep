/**************************************************************************
 * 文件名: main.c
 * 说  明: GZ038 第6套 子任务2-3 智能设备开发(NB-IoT 板)
 * 平  台: NB-IoT 节点板(在赛题提供的未完成工程上补全)，main.c + board.h
 *
 * 赛题要求回顾:
 *   1) 通电后 LED2 灭，液晶屏显示第 1 屏效果;
 *   2) 按下 KEY2 -> LED2 微微发亮，液晶屏切换到第 2 屏效果;
 *   3) 按下 KEY3 -> LED2 完全亮起，液晶屏切换到第 3 屏效果;
 *   4) 可重复按键切换。
 *
 * 注: 三屏 LCD 具体图文效果以赛题提供的图片资源为准，
 *     这里用 LCD_ShowScreen(0/1/2) 切换原工程已有的三屏画面。
 **************************************************************************/
#include "board.h"

#define DEBOUNCE_MS   20

/* 全局: 当前亮度/屏幕状态机 0=灭 1=微亮 2=全亮 */
static uint8_t g_level = LED2_LEVEL_OFF;

static uint32_t tKey2=0, tKey3=0;
static uint8_t  sKey2=1, sKey3=1;

/* 按档位设置 LED2 亮度与 LCD 屏幕 */
static void ApplyLevel(uint8_t lv)
{
  g_level = lv;
  switch (lv) {
    case LED2_LEVEL_OFF:
      Led2_SetDuty(DUTY_OFF);            /* 灭 */
      LCD_ShowScreen(0);                /* 第 1 屏 */
      break;
    case LED2_LEVEL_DIM:
      Led2_SetDuty(DUTY_DIM);            /* 微亮 */
      LCD_ShowScreen(1);                 /* 第 2 屏 */
      break;
    case LED2_LEVEL_FULL:
    default:
      Led2_SetDuty(DUTY_FULL);           /* 全亮 */
      LCD_ShowScreen(2);                 /* 第 3 屏 */
      break;
  }
}

/* 非阻塞按键扫描: 返回 2/3 表示新按下 */
static uint8_t Key_Scan(void)
{
  uint32_t now = SysTick_GetMs();
  uint8_t ev = 0;

  if (KEY2_DOWN()) {
    if (sKey2 && (now - tKey2 >= DEBOUNCE_MS)) { ev = 2; sKey2 = 0; tKey2 = now; }
  } else { sKey2 = 1; tKey2 = now; }

  if (KEY3_DOWN()) {
    if (sKey3 && (now - tKey3 >= DEBOUNCE_MS)) { ev = 3; sKey3 = 0; tKey3 = now; }
  } else { sKey3 = 1; tKey3 = now; }

  return ev;
}

int main(void)
{
  Board_Init();
  SysTick_Start();

  /* 上电: LED2 灭, LCD 第 1 屏 */
  ApplyLevel(LED2_LEVEL_OFF);

  while (1) {
    uint8_t key = Key_Scan();
    if (key == 2) {
      /* KEY2 -> 微亮 + 第2屏 */
      ApplyLevel(LED2_LEVEL_DIM);
    } else if (key == 3) {
      /* KEY3 -> 全亮 + 第3屏 */
      ApplyLevel(LED2_LEVEL_FULL);
    }
    /* 可重复: 再次按 KEY2/KEY3 在两档间切换;
       若需回到灭档可在此扩展(赛题未要求, 保持按赛题行为)。 */
  }
}
