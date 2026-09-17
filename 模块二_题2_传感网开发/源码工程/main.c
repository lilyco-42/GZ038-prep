/*============================================================================
 * main.c  子任务2-2 传感网开发: 按键控制 LED 程序
 *----------------------------------------------------------------------------
 * 硬件: 新大陆蓝色 ZigBee 节点盒
 * 按键: SW1   灯: LED1 / LED2
 *
 * 任务要求(逐条对应):
 *   [1] 节点盒通电或重置: LED1、LED2 都不亮。
 *   [2] 长按 SW1 不松开:  LED1 亮, LED2 熄灭。
 *   [3] 松开 SW1:         LED1、LED2 都常亮。
 *   [4] 双击 SW1:         LED1 进入呼吸灯效果, LED2 保持熄灭。
 *   [5] 再次双击 SW1:     LED1 维持当前亮度不再变化, LED2 继续熄灭。
 *
 * 设计思路:
 *   在 5ms 定时中断里做按键扫描, 维护"按下计数/释放计数", 用状态机区分
 *   单击(长按)/双击; 呼吸灯用 PWM 占空比三角波(0->100->0)循环实现。
 *
 * 按键事件状态机:
 *   空闲(IDLE) --按下--> 计时中(PRESSING)
 *   PRESSING:
 *     - 若先释放且持续时间 < 长按阈值 -> 短按, 进入"等待第二次按下"窗口
 *       窗口内再次按下并释放 -> 双击(DOUBLE_CLICK)
 *       窗口超时           -> 单击已结束(本任务单击不触发特殊动作)
 *     - 若持续时间 >= 长按阈值 -> 长按成立(LONG_HOLD), 期间 LED1 亮/LED2 灭
 *       释放 -> 进入"全亮"状态(ALL_ON)
 *==========================================================================*/
#include "board.h"

/*------------------------- 按键事件枚举 ------------------------------------*/
typedef enum {
    EV_NONE = 0,      /* 无事件 */
    EV_LONG_HOLD,     /* 长按成立(仍按着) */
    EV_LONG_RELEASE,  /* 长按后松开 */
    EV_DOUBLE_CLICK   /* 双击完成 */
} KeyEvent;

/*------------------------- LED 工作模式枚举 --------------------------------*/
typedef enum {
    MODE_INIT = 0,    /* 初始: 两灯全灭 */
    MODE_LONG_HOLD,   /* 长按中: LED1 亮, LED2 灭 */
    MODE_ALL_ON,      /* 长按松开后: 两灯常亮 */
    MODE_BREATH,      /* 双击: LED1 呼吸, LED2 灭 */
    MODE_BREATH_HOLD  /* 再双击: LED1 冻结当前亮度, LED2 灭 */
} LedMode;

/*------------------------- 全局变量 ----------------------------------------*/
static LedMode  g_mode = MODE_INIT;   /* 当前灯模式 */
static unsigned long g_tick = 0;      /* 系统节拍, 每 KEY_SCAN_PERIOD_MS 加 1 */

/* 按键消抖/识别变量 */
static unsigned char  key_level_stable = 1;   /* 1=松开, 0=按下(消抖后的电平) */
static unsigned long  press_tick = 0;         /* 本次按下开始的节拍 */
static unsigned long  release_tick = 0;       /* 上次松开的节拍 */
static unsigned char  long_fired = 0;        /* 本次按下是否已经触发过长按 */
static unsigned char  got_first_short = 0;    /* 是否记录到"第一次短按" */

/* 呼吸灯变量 */
static unsigned char  breath_duty = 0;        /* 当前占空比 0~100 */
static signed char    breath_dir = 1;         /* 1=渐亮, -1=渐暗 */
static unsigned long  breath_tick_cnt = 0;    /* 呼吸步进计时 */
static unsigned char  frozen_duty = 0;        /* 冻结时保存的占空比 */

/*============================================================================
 * 按键扫描(在 5ms 定时中断中周期调用)
 * 返回本次扫描识别出的事件, 多数时候返回 EV_NONE
 *==========================================================================*/
static KeyEvent Key_Scan(void)
{
    KeyEvent ev = EV_NONE;
    unsigned char raw = Key_SW1_Down();      /* 1=按下, 0=松开 */

    /* 简单消抖: 直接读取原始电平, 这里用稳定电平比较 */
    unsigned char stable = raw ? 0 : 1;      /* 板上按下为低, 统一成 1=按下 */

    if (stable != key_level_stable) {
        /* 状态发生跳变, 可在此加滤波计数; 竞赛节点盒抖动小, 直接采纳 */
        key_level_stable = stable;
        if (stable == 1) {
            /* ---- 一次新的按下 ---- */
            press_tick = g_tick;
            long_fired = 0;
            if (got_first_short &&
                (g_tick - release_tick) * KEY_SCAN_PERIOD_MS < KEY_DOUBLE_GAP_MS) {
                /* 在双击窗口内再次按下 -> 判定为双击完成 */
                got_first_short = 0;
                ev = EV_DOUBLE_CLICK;
            }
        } else {
            /* ---- 一次释放 ---- */
            release_tick = g_tick;
            if (long_fired) {
                /* 这是"长按"之后松开 */
                ev = EV_LONG_RELEASE;
            } else {
                /* 短按松开: 记一次短按, 等待第二次按下判断双击 */
                got_first_short = 1;
            }
        }
    } else {
        /* 电平保持, 进行长按/双击窗口超时判断 */
        if (stable == 1 && !long_fired) {
            /* 按着且还没判过长按 */
            if ((g_tick - press_tick) * KEY_SCAN_PERIOD_MS >= KEY_LONG_PRESS_MS) {
                long_fired = 1;
                ev = EV_LONG_HOLD;            /* 长按成立事件 */
            }
        }
        if (got_first_short &&
            (g_tick - release_tick) * KEY_SCAN_PERIOD_MS >= KEY_DOUBLE_GAP_MS) {
            /* 双击窗口超时, 本次只是个单击, 不做动作 */
            got_first_short = 0;
        }
    }
    return ev;
}

/*============================================================================
 * 根据当前模式刷新 LED 硬件输出
 *==========================================================================*/
static void Led_Refresh(void)
{
    switch (g_mode) {
    case MODE_INIT:                 /* 上电/复位: 全灭 */
        LED1_OFF();
        LED2_OFF();
        PWM_SetDuty(0);
        break;

    case MODE_LONG_HOLD:            /* 长按中: LED1 亮, LED2 灭 */
        PWM_SetDuty(BREATH_LEVEL_MAX);   /* LED1 全亮 */
        LED1_ON();
        LED2_OFF();
        break;

    case MODE_ALL_ON:               /* 长按松开: 两灯常亮 */
        LED1_ON();
        LED2_ON();
        PWM_SetDuty(BREATH_LEVEL_MAX);
        break;

    case MODE_BREATH:               /* LED1 呼吸, LED2 灭 */
        LED2_OFF();
        PWM_SetDuty(breath_duty);
        break;

    case MODE_BREATH_HOLD:          /* LED1 冻结, LED2 灭 */
        LED2_OFF();
        PWM_SetDuty(frozen_duty);
        break;

    default:
        break;
    }
}

/*============================================================================
 * 呼吸灯占空比推进(在 5ms 中断里按 BREATH_STEP_MS 节拍调用)
 *==========================================================================*/
static void Breath_Step(void)
{
    breath_duty += breath_dir * 2;             /* 每次步进 2%, 调节呼吸幅度 */
    if (breath_duty >= BREATH_LEVEL_MAX) {
        breath_duty = BREATH_LEVEL_MAX;
        breath_dir = -1;                       /* 到最亮后转暗 */
    } else if (breath_duty == 0 || breath_duty > BREATH_LEVEL_MAX) {
        breath_duty = 0;
        breath_dir = 1;                        /* 到最暗后转亮 */
    }
}

/*============================================================================
 * 事件处理: 把按键事件翻译成模式切换
 *==========================================================================*/
static void On_Event(KeyEvent ev)
{
    switch (ev) {
    case EV_LONG_HOLD:              /* [2] 长按不松开 */
        g_mode = MODE_LONG_HOLD;
        break;

    case EV_LONG_RELEASE:           /* [3] 松开长按 -> 两灯常亮 */
        g_mode = MODE_ALL_ON;
        break;

    case EV_DOUBLE_CLICK:           /* [4]/[5] 双击切换呼吸灯启停 */
        if (g_mode != MODE_BREATH) {
            /* 第一次双击: 进入呼吸 */
            g_mode = MODE_BREATH;
            breath_duty = 0;
            breath_dir = 1;
        } else {
            /* 第二次双击: 冻结当前亮度 */
            frozen_duty = breath_duty;
            g_mode = MODE_BREATH_HOLD;
        }
        break;

    default:
        break;
    }
}

/*============================================================================
 * 5ms 定时中断服务函数(在 bsp.c 的定时器中断里调用本函数)
 *==========================================================================*/
void Timer_ISR_5ms(void)
{
    g_tick++;

    KeyEvent ev = Key_Scan();
    if (ev != EV_NONE) {
        On_Event(ev);
    }

    /* 呼吸灯按节拍推进 */
    if (g_mode == MODE_BREATH) {
        breath_tick_cnt++;
        if (breath_tick_cnt >= (BREATH_STEP_MS / KEY_SCAN_PERIOD_MS)) {
            breath_tick_cnt = 0;
            Breath_Step();
        }
    }

    Led_Refresh();
}

/*============================================================================
 * 主函数
 *==========================================================================*/
int main(void)
{
    Board_Init();                  /* 初始化 IO / 定时器 / 上拉 */
    g_mode = MODE_INIT;            /* [1] 上电初始两灯全灭 */
    Led_Refresh();

    while (1) {
        /* 所有工作都在 5ms 定时中断里完成, 主循环可进入低功耗或空转 */
        /* 如需 ZigBee 组网/上报, 在此调用网络协议栈处理函数 */
    }
}
