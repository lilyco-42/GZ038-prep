/*****************************************************************************
 * 文件名称 : main.h
 * 所属任务 : GZ038 第4套 模块二 子任务2-3 计数器系统开发
 * 硬件平台 : NB-IoT 模块
 * 说明     : 板级驱动接口声明, 实际工程按模块 BSP 补齐寄存器实现。
 ****************************************************************************/
#ifndef __MAIN_H__
#define __MAIN_H__

typedef unsigned char  uint8;
typedef unsigned short uint16;
typedef unsigned int   uint32;

/* 系统与延时 */
void SystemClock_Init(void);
void Delay_ms(uint32 ms);

/* LED2 指示灯: 1=亮 0=灭 */
void Led2_Init(void);
void Led2_Write(uint8 on);

/* 三个按键: 返回 1 表示按下(低电平有效时在驱动层做极性转换) */
void Key_Init(void);
uint8 Key2_Pressed(void);
uint8 Key3_Pressed(void);
uint8 Key4_Pressed(void);

/* 液晶屏 */
void Lcd_Init(void);
void Lcd_Clear(void);
void Lcd_ShowString(uint8 x, uint8 y, const uint8 *str);
/* 在"数值/结果"行显示 形如 "N: 123", label 为前缀字符串 */
void Lcd_ShowNumLine(const char *label, uint32 value);

/* 片内 Flash: 读 / 写 / 擦除 */
void Flash_Init(void);
void Flash_Read(uint32 addr, uint8 *buf, uint32 len);
void Flash_Write(uint32 addr, const uint8 *buf, uint32 len);
void Flash_Erase(uint32 addr, uint32 len);

#endif /* __MAIN_H__ */
