plugins {
    id("org.jetbrains.intellij.platform") version "2.1.0"
    kotlin("jvm") version "1.9.25"
}

group = "com.aidevops"
version = "0.1.0"

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        intellijIdeaCommunity("2024.1")
        bundledPlugin("com.intellij.java")
        instrumentationTools()
    }
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.code.gson:gson:2.10.1")
}

intellijPlatform {
    pluginConfiguration {
        id = "com.aidevops.intellij"
        name = "AI DevOps"
        version = "0.1.0"
        description = "AI-powered DevOps automation: scan, generate Docker/CI-CD, deploy, analyze failures."
        changeNotes = "Initial release"
        ideaVersion {
            sinceBuild = "241"
            untilBuild = "243.*"
        }
    }
    signing {
        // 로컬 개발: 서명 생략
    }
    publishing {
        // JetBrains Marketplace 배포 시 설정
    }
}

kotlin {
    jvmToolchain(17)
}
