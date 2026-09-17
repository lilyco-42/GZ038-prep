/*****************************************************************************
 * 文件名称 : main.c
 * 所属任务 : GZ038 第4套 模块二 子任务2-3 计数器系统开发
 * 硬件平台 : NB-IoT 模块(在赛项提供的未完成工程上补全功能)
 *
 * 功能需求:
 *   1. 通电后 LED2 灭, 液晶屏显示:
 *          计数器
 *          数值: N
 *          结果: Y
 *      (N 为自然数, 即 0,1,2,...)
 *   2. 按 Key2 -> 当前数值 N = N - 1
 *   3. 按 Key3 -> 当前数值 N = N + 1
 *   4. 结果 Y 由公式将 N 代入得出(本工程取 Y = N * N, 即平方,
 *      公式可在 FORMULA_Y 处按裁判给定口径修改)。
 *   5. 按 Key4 -> 把当前 N 写入模块 Flash 保存, 同时 LED2 亮 1 秒后熄灭。
 *   6. 模块断电重新上电或复位后, 液晶屏 N 显示为"最后一次保存到 Flash
 *      中的数值"(上电先从 Flash 读出上次保存的 N)。
 ****************************************************************************/

#include "main.h"

/*---------------------------- 引脚/常量约定 -------------------------------*/
#define LED2_ON()      Led2_Write(1)     /* LED2 亮 */
#define LED2_OFF()     Led2_Write(0)     /* LED2 灭 */

#define KEY2_MIN_VALUE 0                 /* N 下限: 自然数不能为负 */
/* 结果公式: Y = N*N。N 较大时为防溢出按 32 位运算。 */
#define FORMULA_Y(n)   ((uint32)(n) * (uint32)(n))

/* Flash 中保存 N 的偏移地址(按模块 Flash 分区, 选用户可用区) */
#define FLASH_SAVE_ADDR   0x0000

/* Flash 中"已保存"标志, 用于判断是否首次使用 */
#define FLASH_VALID_FLAG  0xA55A

/*---------------------------- 全局变量 -----------------------------------*/
static uint32 s_number = 0;     /* 当前数值 N(自然数) */
static uint32 s_result = 0;     /* 结果 Y */

/*---------------------------------------------------------------------------
 * 函数: uint32 ComputeResult(uint32 n)
 * 描述: 把 N 代入公式求 Y。
 *---------------------------------------------------------------------------*/
static uint32 ComputeResult(uint32 n)
{
    return FORMULA_Y(n);
}

/*---------------------------------------------------------------------------
 * 函数: void RefreshDisplay(void)
 * 描述: 在液晶屏上刷新三行: 计数器 / 数值: N / 结果: Y
 *---------------------------------------------------------------------------*/
static void RefreshDisplay(void)
{
    Lcd_Clear();
    Lcd_ShowString(0, 0, (uint8 *)"Counter");        /* 第一行标题: 计数器 */

    Lcd_ShowNumLine("N:", s_number);                 /* 第二行: 数值: N */
    Lcd_ShowNumLine("Y:", s_result);                  /* 第三行: 结果: Y */
}

/*---------------------------------------------------------------------------
 * 函数: void LoadFromFlash(void)
 * 描述: 上电从 Flash 读取上次保存的 N; 若标志无效(首次)则 N=0。
 *---------------------------------------------------------------------------*/
static void LoadFromFlash(void)
{
    uint16 flag = 0;
    uint32 saved = 0;

    Flash_Read(FLASH_SAVE_ADDR, (uint8 *)&flag, sizeof(flag));
    if (flag == FLASH_VALID_FLAG)
    {
        Flash_Read(FLASH_SAVE_ADDR + sizeof(flag),
                   (uint8 *)&saved, sizeof(saved));
        s_number = saved;
    }
    else
    {
        s_number = 0;            /* 首次使用: 从 0 开始 */
    }
    s_result = ComputeResult(s_number);
}

/*---------------------------------------------------------------------------
 * 函数: void SaveToFlash(void)
 * 描述: 把当前 N 连同有效标志写入 Flash。
 *---------------------------------------------------------------------------*/
static void SaveToFlash(void)
{
    uint16 flag = FLASH_VALID_FLAG;

    Flash_Erase(FLASH_SAVE_ADDR, sizeof(flag) + sizeof(s_number));
    Flash_Write(FLASH_SAVE_ADDR, (uint8 *)&flag, sizeof(flag));
    Flash_Write(FLASH_SAVE_ADDR + sizeof(flag),
                (uint8 *)&s_number, sizeof(s_number));
}

/*---------------------------------------------------------------------------
 * 函数: void OnKey2(void)   N = N - 1
 *---------------------------------------------------------------------------*/
static void OnKey2(void)
{
    if (s_number > KEY2_MIN_VALUE)
    {
        s_number--;
    }
    s_result = ComputeResult(s_number);
    RefreshDisplay();
}

/*---------------------------------------------------------------------------
 * 函数: void OnKey3(void)   N = N + 1
 *---------------------------------------------------------------------------*/
static void OnKey3(void)
{
    s_number++;
    s_result = ComputeResult(s_number);
    RefreshDisplay();
}

/*---------------------------------------------------------------------------
 * 函数: void OnKey4(void)   保存 N 到 Flash, LED2 亮 1 秒后灭
 *---------------------------------------------------------------------------*/
static void OnKey4(void)
{
    SaveToFlash();          /* 保存当前 N */
    LED2_ON();              /* LED2 亮 */
    Delay_ms(1000);         /* 保持 1 秒 */
    LED2_OFF();             /* 1 秒后熄灭 */
}

/*---------------------------------------------------------------------------
 * 函数: void Key_ScanTask(void)
 * 描述: 扫描 Key2/Key3/Key4, 软件消抖并等待释放。
 *---------------------------------------------------------------------------*/
static void Key_ScanTask(void)
{
    if (Key2_Pressed())
    {
        Delay_ms(20);
        if (Key2_Pressed())
        {
            OnKey2();
            while (Key2_Pressed()) { Delay_ms(1); }
            Delay_ms(20);
        }
    }
    else if (Key3_Pressed())
    {
        Delay_ms(20);
        if (Key3_Pressed())
        {
            OnKey3();
            while (Key3_Pressed()) { Delay_ms(1); }
            Delay_ms(20);
        }
    }
    else if (Key4_Pressed())
    {
        Delay_ms(20);
        if (Key4_Pressed())
        {
            OnKey4();
            while (Key4_Pressed()) { Delay_ms(1); }
            Delay_ms(20);
        }
    }
}

/*---------------------------------------------------------------------------
 * 主函数
 *---------------------------------------------------------------------------*/
void main(void)
{
    /* 上电初始化 */
    SystemClock_Init();
    Led2_Init();
    Lcd_Init();
    Key_Init();
    Flash_Init();

    LED2_OFF();                 /* 通电后 LED2 灭 */
    LoadFromFlash();            /* 从 Flash 读出上次保存的 N */
    RefreshDisplay();           /* 显示 计数器/数值:N/结果:Y */

    while (1)
    {
        Key_ScanTask();         /* 循环扫描三个按键 */
        Delay_ms(10);
    }
}
