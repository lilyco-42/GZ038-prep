GZ038 第9套 子任务2-5  室内温湿度 (Android)
=========================================================

工程: 室内温湿度/  (标准 Android Gradle 工程, Java)
  build.gradle / settings.gradle / gradle.properties
  app/build.gradle, app/proguard-rules.pro
  app/src/main/AndroidManifest.xml
  app/src/main/java/com/newland/roomtemp/
      MainActivity.java   轮询云服务, 显示温度/湿度
      CloudClient.java    云服务 REST 客户端
  app/src/main/res/       layout/values/drawable

界面色号(赛题硬要求):
  "温度""湿度"标签  -> 白色 #FFFFFF
  温度监测值        -> #01A7FF
  湿度监测值        -> #35D529

数据来源: 云服务 192.168.0.138, 传感器标识 温度=m_temp, 湿度=m_hum, 2秒刷新。
未连云服务时自动显示演示数据, 便于界面验收。

部署: Android Studio 打开本目录编译, 安装到物联网应用开发终端, 应用名"室内温湿度"。
打包: 室内温湿度.rar -> D:\提交资料\模块二\题5
