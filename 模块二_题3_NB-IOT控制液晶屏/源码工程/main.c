/****************************************************************************
 * 子任务2-3  NB-IoT 节点盒 液晶屏日期设置程序
 *--------------------------------------------------------------------------*
 * 平台：NB-IoT 智慧盒（MCU 通用裸机 C，LCD + 4 按键 KEY1~KEY4 + LED2 +
 *       一路串口）。本文件把 LCD / 串口 / 按键 统一抽象成 HAL 函数，
 *       业务状态机与板级驱动解耦，移植时只需实现 hal_* 几个空函数。
 *
 * 赛题要求（严格按任务书实现）：
 *   【初始运行图】显示当前日期：年、月、日。
 *   【设置图】按 KEY4 进入：黑色三角 "▲" 表示当前设置项；
 *             KEY2 上移三角，KEY3 下移三角。
 *   【修改态】在设置图按 KEY4：当前项前出现 "*"，板上 LED2 点亮，
 *             表示该项可修改；KEY2 = 该项 +1，KEY3 = 该项 -1。
 *   按 KEY4 退出修改态："*" 消失，LED2 熄灭，保存当前值，返回设置图。
 *   【串口远程改日期】开发机串口下发十六进制命令帧，NB-IoT 接收后自动
 *             修改年/月/日，并回：成功 0xFB 0x00 0xFE / 失败 0xFB 0x01 0xFE。
 *   【返回运行图】设置图状态下按 KEY1 复位键 -> 返回初始运行图，显示新日期。
 *
 * 串口命令帧格式（小端/大端说明见下）：
 *   帧结构:  0xFB | 类型字节 | 数据... | 0xFE
 *   类型 0x01 改年:  0xFB 0x01 年1 年2 0xFE   (例: 0xFB 0x01 0x14 0x15 0xFE -> 2021)
 *              年1=年份高两位(20), 年2=年份低两位(21)，year = 年1*100 + 年2
 *   类型 0x02 改月:  0xFB 0x02 月     0xFE   (例: 0xFB 0x02 0x0A 0xFE -> 10月)
 *   类型 0x03 改日:  0xFB 0x03 日     0xFE   (例: 0xFB 0x03 0x0C 0xFE -> 12日)
 *--------------------------------------------------------------------------*
 * 按键映射（板上丝印）：KEY1=复位/返回  KEY2=上移或加  KEY3=下移或减  KEY4=确认/进入
 ****************************************************************************/

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/*=========================== HAL 抽象（按实际板子实现） ===================*/
/* 以下 6 个函数在真实板级 BSP 中实现；这里给出声明与空壳，便于状态机编译。*/

/* LCD 初始化 / 清屏 */
extern void HAL_Lcd_Init(void);
extern void HAL_Lcd_Clear(void);
/* 在 (col,row) 处显示以 '\0' 结尾的字符串 */
extern void HAL_Lcd_ShowStr(uint8_t col, uint8_t row, const char *s);

/* LED2 控制：on=true 点亮 */
extern void HAL_Led2_Set(bool on);

/* 串口发送 n 个字节 */
extern void HAL_Uart_Send(const uint8_t *data, uint16_t n);

/* 按键扫描：返回本次按下的键码；无按键返回 0。
   键码约定：1=KEY1  2=KEY2  3=KEY3  4=KEY4；返回 0 表示无键。 */
extern uint8_t HAL_Key_Scan(void);

/* 系统毫秒级延时 */
extern void HAL_DelayMs(uint16_t ms);

/*=========================== 业务常量 ====================================*/

/* 帧头帧尾与命令类型 */
#define FRAME_HEAD        0xFB
#define FRAME_TAIL        0xFE
#define CMD_TYPE_YEAR     0x01
#define CMD_TYPE_MONTH    0x02
#define CMD_TYPE_DAY      0x03

/* 串口应答 */
#define ACK_OK            0x00
#define ACK_FAIL          0x01

/* 最大帧长（帧头+类型+2数据+帧尾=5） */
#define UART_BUF_MAX      8

/* 界面状态机 */
typedef enum {
    UI_RUN = 0,     /* 运行图：显示日期 */
    UI_SETTING,     /* 设置图：三角选择设置项 */
    UI_EDIT         /* 修改态：带 "*"，正在改某项 */
} UiState;

/* 设置项索引 */
enum {
    ITEM_YEAR = 0,
    ITEM_MONTH,
    ITEM_DAY,
    ITEM_MAX
};

/*=========================== 全局数据 ====================================*/

static uint16_t g_year  = 2021;   /* 默认日期，可由 RTC/串口/按键修改 */
static uint8_t  g_month = 1;
static uint8_t  g_day   = 1;

static UiState  g_state = UI_RUN;
static uint8_t  g_sel   = ITEM_YEAR;   /* 当前选中的设置项 */

/* 串口接收状态机缓存 */
static uint8_t  g_rx_buf[UART_BUF_MAX];
static uint8_t  g_rx_len = 0;

/*=========================== 工具函数 ====================================*/

/* 数字转两位 ASCII（0~99），写入 out（至少3字节，含结束符） */
static void TwoDigits(uint8_t v, char *out)
{
    out[0] = (char)('0' + v / 10);
    out[1] = (char)('0' + v % 10);
    out[2] = '\0';
}

/* 范围钳制 */
static uint8_t ClampU8(uint8_t v, uint8_t lo, uint8_t hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

/* 应答一帧：0xFB 0x(code) 0xFE */
static void SendAck(uint8_t code)
{
    uint8_t frame[3] = {FRAME_HEAD, code, FRAME_TAIL};
    HAL_Uart_Send(frame, 3);
}

/* 按修改范围对当前选中项做 +1/-1（带回绕与合法范围） */
static void AdjustSelected(int8_t delta)
{
    if (g_sel == ITEM_YEAR)
    {
        int y = (int)g_year + delta;
        if (y < 2000) y = 2099;       /* 回绕 */
        if (y > 2099) y = 2000;
        g_year = (uint16_t)y;
    }
    else if (g_sel == ITEM_MONTH)
    {
        int m = (int)g_month + delta;
        if (m < 1)  m = 12;
        if (m > 12) m = 1;
        g_month = (uint8_t)m;
    }
    else /* ITEM_DAY */
    {
        int d = (int)g_day + delta;
        if (d < 1)  d = 31;
        if (d > 31) d = 1;
        g_day = (uint8_t)d;
    }
}

/*=========================== 界面绘制 ====================================*/

/* 运行图：显示当前日期 年-月-日 */
static void DrawRunScreen(void)
{
    char buf[16];
    HAL_Lcd_Clear();
    HAL_Lcd_ShowStr(0, 0, "Run:");
    /* 年：4 位 */
    TwoDigits((uint8_t)(g_year / 100), buf);            buf[2] = (char)('0' + (g_year / 10) % 10);
    buf[3] = (char)('0' + g_year % 10); buf[4] = '\0';
    HAL_Lcd_ShowStr(0, 1, buf);
    HAL_Lcd_ShowStr(4, 1, "-");
    TwoDigits(g_month, buf);  HAL_Lcd_ShowStr(5, 1, buf);
    HAL_Lcd_ShowStr(7, 1, "-");
    TwoDigits(g_day, buf);    HAL_Lcd_ShowStr(8, 1, buf);
}

/* 设置图：三项菜单，黑色三角 ▲ 指向当前项；修改态当前项前加 "*" */
static void DrawSettingScreen(void)
{
    char buf[16];
    uint8_t row;
    HAL_Lcd_Clear();
    HAL_Lcd_ShowStr(0, 0, "Set:");

    /* 行1=年, 行2=月, 行3=日（行号按 LCD 行数自行调整） */
    const char *names[ITEM_MAX] = {"Y", "M", "D"};
    for (uint8_t i = 0; i < ITEM_MAX; i++)
    {
        row = 1 + i;
        /* 三角标记当前选中项 */
        if (i == g_sel)
            HAL_Lcd_ShowStr(0, row, ">");      /* 用 ">" 代表黑色三角 ▲ */
        else
            HAL_Lcd_ShowStr(0, row, " ");

        /* 修改态：当前项前加 "*" */
        if (g_state == UI_EDIT && i == g_sel)
            HAL_Lcd_ShowStr(1, row, "*");
        else
            HAL_Lcd_ShowStr(1, row, " ");

        /* 项目名 */
        HAL_Lcd_ShowStr(2, row, names[i]);

        /* 数值 */
        if (i == ITEM_YEAR)
        {
            TwoDigits((uint8_t)(g_year / 100), buf);
            buf[2] = (char)('0' + (g_year / 10) % 10);
            buf[3] = (char)('0' + g_year % 10); buf[4] = '\0';
            HAL_Lcd_ShowStr(4, row, buf);
        }
        else if (i == ITEM_MONTH)
        {
            TwoDigits(g_month, buf);
            HAL_Lcd_ShowStr(4, row, buf);
        }
        else
        {
            TwoDigits(g_day, buf);
            HAL_Lcd_ShowStr(4, row, buf);
        }
    }
}

/*=========================================================================*
 * 串口命令帧处理。在主循环中对每个新收到的字节调用一次。
 * 协议：0xFB | 类型 | 数据... | 0xFE
 *=======================================================================*/
static void OnUartByte(uint8_t b)
{
    /* 帧头同步 */
    if (g_rx_len == 0)
    {
        if (b == FRAME_HEAD)
        {
            g_rx_buf[0] = b;
            g_rx_len = 1;
        }
        return;
    }

    /* 收到帧尾：组装完成，解析 */
    if (b == FRAME_TAIL)
    {
        bool ok = false;
        /* g_rx_buf[0]=0xFB, g_rx_buf[1]=类型, [2..]=数据, 末尾刚收 0xFE */
        if (g_rx_len >= 3)
        {
            uint8_t type = g_rx_buf[1];
            if (type == CMD_TYPE_YEAR && g_rx_len == 4)
            {
                /* 0xFB 0x01 年1 年2 */
                g_year = (uint16_t)g_rx_buf[2] * 100 + g_rx_buf[3];
                ok = true;
            }
            else if (type == CMD_TYPE_MONTH && g_rx_len == 3)
            {
                /* 0xFB 0x02 月 */
                uint8_t m = g_rx_buf[2];
                if (m >= 1 && m <= 12) { g_month = m; ok = true; }
            }
            else if (type == CMD_TYPE_DAY && g_rx_len == 3)
            {
                /* 0xFB 0x03 日 */
                uint8_t d = g_rx_buf[2];
                if (d >= 1 && d <= 31) { g_day = d; ok = true; }
            }
        }
        SendAck(ok ? ACK_OK : ACK_FAIL);
        g_rx_len = 0;
        return;
    }

    /* 普通数据字节：入缓存，防止溢出 */
    if (g_rx_len < UART_BUF_MAX - 1)
    {
        g_rx_buf[g_rx_len++] = b;
    }
    else
    {
        g_rx_len = 0;   /* 超长，丢弃重新同步 */
    }
}

/*=========================================================================*
 * 按键处理：根据当前界面状态分发
 *=======================================================================*/
static void OnKey(uint8_t key)
{
    if (key == 0) return;

    switch (g_state)
    {
    case UI_RUN:
        /* 运行图：只有 KEY4 进入设置图 */
        if (key == 4)
        {
            g_state = UI_SETTING;
            g_sel   = ITEM_YEAR;
            DrawSettingScreen();
        }
        break;

    case UI_SETTING:
        /* 设置图：
           KEY2 上移三角，KEY3 下移三角，KEY4 进入修改态，KEY1 返回运行图 */
        if (key == 2)
        {
            if (g_sel > 0) g_sel--;
            DrawSettingScreen();
        }
        else if (key == 3)
        {
            if (g_sel < ITEM_MAX - 1) g_sel++;
            DrawSettingScreen();
        }
        else if (key == 4)
        {
            g_state = UI_EDIT;          /* 进入修改态：显示 "*"，点亮 LED2 */
            HAL_Led2_Set(true);
            DrawSettingScreen();
        }
        else if (key == 1)
        {
            /* KEY1 复位：返回运行图，显示新日期 */
            g_state = UI_RUN;
            DrawRunScreen();
        }
        break;

    case UI_EDIT:
        /* 修改态：
           KEY2 该项 +1，KEY3 该项 -1，KEY4 保存并退出修改态 */
        if (key == 2)
        {
            AdjustSelected(+1);
            DrawSettingScreen();
        }
        else if (key == 3)
        {
            AdjustSelected(-1);
            DrawSettingScreen();
        }
        else if (key == 4)
        {
            g_state = UI_SETTING;       /* 关闭 "*"，熄灭 LED2，保存(已在内存) */
            HAL_Led2_Set(false);
            DrawSettingScreen();
        }
        else if (key == 1)
        {
            /* 修改态下 KEY1 也复位回运行图（题目要求设置图状态下 KEY1 返回；
               修改态属于设置流程，一并复位返回并显示最新日期） */
            HAL_Led2_Set(false);
            g_state = UI_RUN;
            DrawRunScreen();
        }
        break;
    }
}

/*=========================================================================*
 * 主函数
 *=======================================================================*/
int main(void)
{
    HAL_Lcd_Init();
    HAL_Led2_Set(false);
    g_rx_len = 0;
    g_state  = UI_RUN;
    DrawRunScreen();

    while (1)
    {
        /* 1) 处理串口新字节：把 HAL_Uart_Available()/Read() 读到的字节逐个喂入。
           真实工程中通常在 UART 接收中断里直接调用 OnUartByte(byte)。 */
        extern uint8_t HAL_Uart_PollByte(bool *got);
        bool got = false;
        uint8_t b = HAL_Uart_PollByte(&got);
        if (got)
        {
            OnUartByte(b);
            /* 串口改了日期后，若正在运行图则立即刷新显示 */
            if (g_state == UI_RUN) DrawRunScreen();
        }

        /* 2) 扫描按键 */
        uint8_t k = HAL_Key_Scan();
        if (k != 0)
        {
            OnKey(k);
            HAL_DelayMs(20);            /* 简单消抖 */
        }

        HAL_DelayMs(10);
    }
}
