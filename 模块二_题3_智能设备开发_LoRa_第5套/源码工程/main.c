/**************************************************************************
 * 文件名: main.c
 * 说  明: GZ038 第5套 子任务2-3 智能设备开发(LoRa 节点板)
 * 平  台: LoRa 节点板(在赛题提供的未完成工程上补全)，main.c + board.h
 *
 * 赛题要求回顾:
 *   1) 通电后 LED1、LED2 亮，液晶屏显示菜单:
 *        亮灯模式
 *        1.常亮模式 <
 *        2.呼吸模式
 *        3.交替亮灭
 *   2) < 为当前选中项指针: 按 KEY2 上移，按 KEY3 下移；
 *   3) 在 < 所在项按 KEY4: LED1、LED2 进入对应模式:
 *        模式1 常亮  : LED1、LED2 常亮；
 *        模式2 呼吸  : LED1、LED2 呼吸灯(由暗渐亮再渐暗循环)；
 *        模式3 交替  : LED1 亮则 LED2 灭，LED1 灭则 LED2 亮，间隔 0.5 秒；
 *   4) 能重复以上步骤(在任何模式下再次按键切回菜单/切换模式均可)。
 **************************************************************************/
#include "board.h"

/* 菜单项编号 */
#define MODE_STEADY   0     /* 1.常亮模式 */
#define MODE_BREATH   1     /* 2.呼吸模式 */
#define MODE_ALT      2     /* 3.交替亮灭 */
#define MODE_COUNT    3

/* 交替亮灭间隔 500ms; 呼吸灯每个亮度台阶时长 8ms，一次呼吸周期约 2.4s */
#define ALT_PERIOD_MS     500
#define BREATH_STEP_MS    8
#define BREATH_MAX        100

/* 按键消抖 */
#define DEBOUNCE_MS       20

/* 全局状态 */
static uint8_t  g_cursor   = MODE_STEADY;  /* 菜单当前选中项 */
static uint8_t  g_mode     = 0xFF;         /* 已进入的运行模式; 0xFF=停留在菜单 */

/* 呼吸灯状态 */
static uint8_t  g_breDuty   = 0;
static int8_t   g_breDir    = 1;           /* +1 渐亮, -1 渐暗 */

/* 交替亮灭状态 */
static uint8_t  g_altPhase  = 0;            /* 0: LED1亮LED2灭; 1: 反之 */

/* 软件消抖缓存 */
static uint32_t tKey2=0, tKey3=0, tKey4=0;
static uint8_t  sKey2=1, sKey3=1, sKey4=1;

/**************************************************************************
 * 进入某模式时的初始化
 **************************************************************************/
static void EnterMode(uint8_t mode)
{
  g_mode = mode;
  if (mode == MODE_STEADY) {
    LED1_ON(); LED2_ON();                       /* 常亮 */
  } else if (mode == MODE_BREATH) {
    g_breDuty = 0; g_breDir = 1;                /* 从最暗开始呼吸 */
    Led1_SetDuty(0); Led2_SetDuty(0);
  } else if (mode == MODE_ALT) {
    g_altPhase = 0;
    LED1_ON(); LED2_OFF();                      /* LED1 亮则 LED2 灭 */
  }
}

/**************************************************************************
 * 菜单界面: 回到菜单时 LED1、LED2 保持亮(赛题: 通电后两灯亮)
 **************************************************************************/
static void ShowMenu(void)
{
  LCD_Clear();
  LCD_ShowMenu(g_cursor);
  /* 菜单状态两灯常亮，符合"通电后 LED1,LED2 亮" */
  LED1_ON(); LED2_ON();
}

/**************************************************************************
 * 非阻塞按键扫描: 返回本次新按下的键(KEY2/KEY3/KEY4)，无新按返回 0
 **************************************************************************/
static uint8_t Key_Scan(void)
{
  uint32_t now = SysTick_GetMs();
  uint8_t  ev  = 0;

  /* KEY2: 上移 */
  if (KEY2_DOWN()) {
    if (sKey2 && (now - tKey2 >= DEBOUNCE_MS)) { ev = 2; sKey2 = 0; tKey2 = now; }
  } else { sKey2 = 1; tKey2 = now; }

  /* KEY3: 下移 */
  if (KEY3_DOWN()) {
    if (sKey3 && (now - tKey3 >= DEBOUNCE_MS)) { ev = 3; sKey3 = 0; tKey3 = now; }
  } else { sKey3 = 1; tKey3 = now; }

  /* KEY4: 确认 */
  if (KEY4_DOWN()) {
    if (sKey4 && (now - tKey4 >= DEBOUNCE_MS)) { ev = 4; sKey4 = 0; tKey4 = now; }
  } else { sKey4 = 1; tKey4 = now; }

  return ev;
}

/**************************************************************************
 * 呼吸灯周期刷新(每 BREATH_STEP_MS 调用一次)
 **************************************************************************/
static void Breath_Refresh(void)
{
  if (g_mode != MODE_BREATH) return;
  g_breDuty += g_breDir * 2;                       /* 每台阶亮度步进 */
  if (g_breDuty >= BREATH_MAX) { g_breDuty = BREATH_MAX; g_breDir = -1; }
  if (g_breDuty == 0)          { g_breDir = 1; }
  Led1_SetDuty(g_breDuty);
  Led2_SetDuty(g_breDuty);
}

/**************************************************************************
 * 交替亮灭周期刷新(每 ALT_PERIOD_MS 调用一次)
 **************************************************************************/
static void Alt_Refresh(void)
{
  if (g_mode != MODE_ALT) return;
  g_altPhase ^= 1;
  if (g_altPhase) { LED1_OFF(); LED2_ON(); }       /* LED1灭 LED2亮 */
  else            { LED1_ON();  LED2_OFF(); }     /* LED1亮 LED2灭 */
}

/**************************************************************************
 * 主函数
 **************************************************************************/
int main(void)
{
  Board_Init();
  SysTick_Start();

  g_cursor = MODE_STEADY;
  g_mode   = 0xFF;
  ShowMenu();                                      /* 上电两灯亮 + 菜单 */

  uint32_t tBreath = 0, tAlt = 0, now;

  while (1) {
    now = SysTick_GetMs();

    /* 1) 按键处理 */
    uint8_t key = Key_Scan();
    if (key == 2) {                                /* KEY2 上移 */
      if (g_cursor == 0) g_cursor = MODE_COUNT - 1;
      else               g_cursor--;
      ShowMenu();
    } else if (key == 3) {                         /* KEY3 下移 */
      g_cursor = (g_cursor + 1) % MODE_COUNT;
      ShowMenu();
    } else if (key == 4) {                         /* KEY4 确认 -> 进入所选模式 */
      EnterMode(g_cursor);
    }

    /* 2) 运行模式刷新(非阻塞) */
    if (now - tBreath >= BREATH_STEP_MS) {
      tBreath = now;
      Breath_Refresh();
    }
    if (now - tAlt >= ALT_PERIOD_MS) {
      tAlt = now;
      Alt_Refresh();
    }
  }
}
