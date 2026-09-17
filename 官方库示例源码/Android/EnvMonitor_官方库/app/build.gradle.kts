plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.newland.envmonitor"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.newland.envmonitor"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
}

dependencies {
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)
    // 官方硬件调用库（从官方 U 盘/官方例程 依赖 目录拷贝到 app/libs/）
    implementation(files("libs\\nle_hardware_v1.jar"))
    implementation(files("libs\\gson-2.8.1.jar"))
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
}
