GZ038 第6套 子任务2-2 设备无线通讯功能开发 —— 工程说明
====================================================

本任务需要两块黑色 ZigBee(CC2530)板 A、B，建两个 IAR 工程:

  板A工程(标签 A): 加入 main_A.c + board.h + protocol.h
  板B工程(标签 B): 加入 main_B.c + board.h + protocol.h

共用文件:
  board.h     LED1/LED2/SW1 引脚与长按/消抖参数
  protocol.h  无线与串口协议(FA 头 / NN 数据 / FB 尾, 命令字 CMD_INC)

接线:
  板B 的 RS232 口 -> 串口线 -> 工作站 COM1
  串口调试助手: 9600 8N1

验证:
  1) 板B 上电先打印 FA 00 FB;
  2) 板A 短按 SW1 一次 -> 板B 串口出现 FA 01 FB;
     再短按 -> FA 02 FB ... 以此类推;
  3) 长按板A SW1 不松: LED1 亮 LED2 灭; 松开: 两灯都常亮。

注意: Z-Stack 工程中 Wireless_SendCmd()/接收回调分别映射到
      AF_DataRequest() 与 AF 数据指示事件，两端端点/簇号在 protocol.h 对齐。
