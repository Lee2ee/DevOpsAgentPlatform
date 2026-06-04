# AI DevOps Agent Platform - IDE Plugin 구조

## 1. 공통 설계 원칙

- Plugin은 **UI + Core Engine 호출** 만 담당
- 비즈니스 로직은 100% Core Engine에 위임
- Core Engine이 미실행 상태면 플러그인이 자동 실행
- 모든 Plugin은 동일한 REST API 사용 (기능 동등성 보장)

---

## 2. IntelliJ Plugin

### 2.1 플러그인 정보

```xml
<!-- plugin.xml -->
<idea-plugin>
  <id>com.aidevops.intellij</id>
  <name>AI DevOps</name>
  <vendor>AIDevOps</vendor>
  <description>AI-powered DevOps automation for IntelliJ IDEA</description>

  <depends>com.intellij.modules.platform</depends>
  <depends>com.intellij.modules.java</depends>

  <extensions defaultExtensionNs="com.intellij">
    <!-- Tool Window -->
    <toolWindow id="AI DevOps"
                anchor="right"
                factoryClass="com.aidevops.intellij.toolwindow.AiDevOpsToolWindowFactory"/>

    <!-- 설정 페이지 -->
    <applicationConfigurable
        instance="com.aidevops.intellij.settings.AiDevOpsConfigurable"/>

    <!-- 프로젝트 서비스 -->
    <projectService
        serviceImplementation="com.aidevops.intellij.service.CoreEngineService"/>
  </extensions>

  <!-- 컨텍스트 메뉴 액션 그룹 -->
  <actions>
    <group id="AiDevOpsGroup" text="AI DevOps" popup="true">
      <add-to-group group-id="ProjectViewPopupMenu" anchor="last"/>
      <action id="AiDevOps.Analyze"
              class="com.aidevops.intellij.actions.AnalyzeProjectAction"
              text="AI Analyze"/>
      <action id="AiDevOps.Deploy"
              class="com.aidevops.intellij.actions.DeployAction"
              text="AI Deploy"/>
      <separator/>
      <action id="AiDevOps.GenerateDocker"
              class="com.aidevops.intellij.actions.GenerateDockerAction"
              text="Generate Docker"/>
      <action id="AiDevOps.GenerateCicd"
              class="com.aidevops.intellij.actions.GenerateCicdAction"
              text="Generate CI/CD"/>
      <separator/>
      <action id="AiDevOps.AnalyzeLogs"
              class="com.aidevops.intellij.actions.AnalyzeLogsAction"
              text="Analyze Logs"/>
      <action id="AiDevOps.AutoFix"
              class="com.aidevops.intellij.actions.AutoFixAction"
              text="Auto Fix"/>
    </group>
  </actions>
</idea-plugin>
```

### 2.2 CoreEngineService

```kotlin
// 핵심: Core Engine HTTP 클라이언트
@Service(Service.Level.PROJECT)
class CoreEngineService(private val project: Project) {

    private val baseUrl = "http://localhost:8765/api/v1"
    private val client = OkHttpClient()

    // Core Engine 실행 여부 확인 + 자동 시작
    fun ensureRunning(): Boolean

    // 프로젝트 스캔
    fun scanProject(path: String): ScanResult

    // Docker 생성
    fun generateDocker(projectId: String): DockerGenerationResult

    // CI/CD 생성
    fun generateCicd(projectId: String, platform: String): CicdGenerationResult

    // 배포 시작 (deployment_id 반환)
    fun startDeploy(projectId: String, serverId: String): String

    // 장애 분석
    fun analyzeFailure(logContent: String): FailureAnalysis

    // WebSocket 구독 (배포 진행상황)
    fun subscribeDeployProgress(deploymentId: String, listener: DeployEventListener)
}
```

### 2.3 Tool Window 구조

```
AI DevOps Tool Window
├── 탭 1: Analysis
│   ├── [Scan Project] 버튼
│   ├── 스캔 결과 트리뷰
│   │   ├── Language: Java 21 (Spring Boot 3.2)
│   │   ├── Database: Oracle, Redis
│   │   └── MQ: Kafka
│   └── [Generate Docker] [Generate CI/CD] 버튼
│
├── 탭 2: Deploy
│   ├── 서버 선택 드롭다운
│   ├── 배포 전략 선택
│   ├── [Deploy] 버튼
│   └── 배포 로그 콘솔 (실시간)
│       BUILD  ✓ (45s)
│       UPLOAD ✓ (12s)
│       DEPLOY ✓ (8s)
│       HEALTH ✓ (5s)
│       ● 배포 완료: http://192.168.1.100:8080
│
└── 탭 3: Logs & Fix
    ├── [Collect Logs] 버튼
    ├── 로그 뷰어
    ├── [Analyze] 버튼
    ├── 분석 결과
    │   └── NullPointerException @ BookingService.java:128
    └── [Generate Fix] → Diff 뷰어 → [Apply]
```

### 2.4 빌드 설정

```kotlin
// build.gradle.kts
plugins {
    id("org.jetbrains.intellij") version "1.17.0"
    kotlin("jvm") version "1.9.0"
}

intellij {
    version.set("2023.3")
    type.set("IC")  // IntelliJ IDEA Community
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.code.gson:gson:2.10.1")
}
```

---

## 3. VSCode Extension

### 3.1 package.json 핵심 설정

```json
{
  "name": "aidevops-vscode",
  "displayName": "AI DevOps",
  "activationEvents": ["onStartupFinished"],
  "contributes": {
    "commands": [
      {"command": "aidevops.analyze",         "title": "AI DevOps: Analyze Project"},
      {"command": "aidevops.deploy",           "title": "AI DevOps: Deploy"},
      {"command": "aidevops.generateDocker",   "title": "AI DevOps: Generate Docker"},
      {"command": "aidevops.generateCicd",     "title": "AI DevOps: Generate CI/CD"},
      {"command": "aidevops.analyzeLogs",      "title": "AI DevOps: Analyze Logs"},
      {"command": "aidevops.autoFix",          "title": "AI DevOps: Auto Fix"}
    ],
    "menus": {
      "explorer/context": [
        {
          "submenu": "aidevops.submenu",
          "when": "explorerResourceIsFolder"
        }
      ]
    },
    "submenus": [
      {
        "id": "aidevops.submenu",
        "label": "AI DevOps"
      }
    ],
    "viewsContainers": {
      "activitybar": [
        {
          "id": "aidevops-sidebar",
          "title": "AI DevOps",
          "icon": "resources/icon.svg"
        }
      ]
    },
    "views": {
      "aidevops-sidebar": [
        {"id": "aidevops.analysis",  "name": "Analysis"},
        {"id": "aidevops.deploy",    "name": "Deploy"},
        {"id": "aidevops.logs",      "name": "Logs & Fix"}
      ]
    },
    "configuration": {
      "properties": {
        "aidevops.coreEnginePort": {
          "type": "number",
          "default": 8765,
          "description": "Core Engine 포트"
        },
        "aidevops.aiProvider": {
          "type": "string",
          "enum": ["ollama", "claude", "openai"],
          "default": "ollama"
        }
      }
    }
  }
}
```

### 3.2 Core Engine 클라이언트 (TypeScript)

```typescript
// src/client/coreEngineClient.ts
export class CoreEngineClient {
    private baseUrl: string;

    constructor(port: number = 8765) {
        this.baseUrl = `http://localhost:${port}/api/v1`;
    }

    async scanProject(path: string): Promise<ScanResult>
    async generateDocker(projectId: string): Promise<DockerResult>
    async generateCicd(projectId: string, platform: string): Promise<CicdResult>
    async startDeploy(projectId: string, serverId: string): Promise<string>
    async analyzeFailure(logContent: string): Promise<FailureAnalysis>

    // WebSocket 연결
    subscribeDeployProgress(
        deploymentId: string,
        onEvent: (event: DeployEvent) => void
    ): WebSocket
}
```

### 3.3 배포 진행 WebView Panel

```typescript
// src/views/deployPanel.ts
export class DeployPanel {
    private panel: vscode.WebviewPanel;

    // HTML/CSS/JS로 배포 진행 상태 표시
    // WebSocket을 통해 실시간 로그 수신
    // 단계별 진행바 표시
}
```

---

## 4. 두 Plugin 공통 흐름

```
우클릭 or Command Palette 실행
          │
          ▼
CoreEngineManager.ensureRunning()
  ├── 포트 8765 응답 확인
  └── 미응답 시 → Core Engine 바이너리 실행
          │
          ▼
사용자 입력 수집 (서버 선택, 옵션 등)
          │
          ▼
Core Engine REST API 호출
          │
          ▼
결과를 Tool Window / WebView에 표시
```

---

## 5. Core Engine 자동 실행 방식

```
Plugin 초기화 시:
1. ~/.aidevops/core-engine (바이너리) 존재 확인
2. 없으면 → 사용자에게 다운로드/설치 안내
3. 있으면 → 포트 8765 LISTEN 여부 확인
4. 미실행이면 → ProcessBuilder로 백그라운드 실행
5. 실행 후 Health Check: GET /api/v1/health → 200 OK 대기
```
