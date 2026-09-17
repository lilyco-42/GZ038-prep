GZ038 第9套 子任务2-4  设备控制应用开发 (Android)
=========================================================

工程: 设备控制/  (标准 Android Gradle 工程, Java)
  build.gradle / settings.gradle / gradle.properties
  app/build.gradle, app/proguard-rules.pro
  app/src/main/AndroidManifest.xml
  app/src/main/java/com/newland/devicecontrol/
      MainActivity.java   界面与逻辑
      CloudClient.java    云服务 REST 客户端(登录/绑定设备/下发命令)
  app/src/main/res/       layout/values/drawable 资源

功能:
  LED灯  开启 -> 下发 m_steady_green=1 (照明灯/常亮绿灯亮)
  LED灯  关闭 -> 下发 m_steady_green=0
  风扇   开启 -> 下发 m_fan=1 (风扇启动)
  风扇   关闭 -> 下发 m_fan=0
  首次使用在底部填云服务地址(默认192.168.0.138)、账号、密码, 点"登录并绑定设备"。

说明:
  1. 用 Android Studio 打开本目录(含 settings.gradle 的目录)即可同步编译;
  2. applicationId=com.newland.devicecontrol, 应用名"设备控制";
  3. 若工位照明灯/风扇的云服务标识与默认不同, 改 MainActivity 顶部
     TAG_LIGHT / TAG_FAN 两个常量即可;
  4. 已开启 usesCleartextTraffic(允许 http 明文访问内网云服务)。

打包: 整个工程压缩为 设备控制.rar, 拷到 D:\提交资料\模块二\题4。
