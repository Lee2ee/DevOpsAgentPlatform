# AI DevOps Agent Platform - Desktop App 구조

## 1. 개요

- **프레임워크**: Tauri 2.x (Rust 백엔드 + WebView 프론트엔드)
- **UI**: React 18 + TypeScript + shadcn/ui + Tailwind CSS
- **상태관리**: Zustand
- **API**: Axios + React Query
- **빌드**: Vite

Tauri는 Core Engine 프로세스를 **sidecar**로 관리한다.
UI는 Core Engine REST API만 사용하며, Tauri 고유 명령은 최소화한다.

---

## 2. Tauri 백엔드 (Rust)

### 역할
- Core Engine 프로세스 sidecar 실행/관리
- 로컬 파일 시스템 접근 (프로젝트 폴더 선택)
- 앱 트레이 아이콘 관리

```toml
# tauri.conf.json (핵심 설정)
{
  "bundle": {
    "externalBin": ["binaries/aidevops-core"]  # Core Engine 바이너리 번들링
  },
  "allowlist": {
    "dialog": {"open": true},          # 폴더 선택 다이얼로그
    "shell": {"sidecar": true},        # Core Engine 실행
    "fs": {"readDir": true}            # 파일 목록 읽기
  }
}
```

```rust
// src-tauri/src/commands.rs
#[tauri::command]
async fn start_core_engine(app: AppHandle) -> Result<(), String> {
    // Core Engine sidecar 실행
    // 이미 실행 중이면 skip
}

#[tauri::command]
async fn select_folder() -> Result<String, String> {
    // OS 네이티브 폴더 선택 다이얼로그
}

#[tauri::command]
fn get_core_engine_port() -> u16 {
    8765
}
```

---

## 3. React 앱 구조

### 3.1 페이지 라우팅

```
/ (Dashboard)
├── /project       (프로젝트 분석)
├── /deploy        (배포 관리)
├── /logs          (로그 & 장애분석)
├── /monitoring    (모니터링)  [Phase 2]
└── /settings      (설정)
```

### 3.2 컴포넌트 트리

```
App
├── Layout
│   ├── Sidebar
│   │   ├── 로고
│   │   ├── NavItem: Dashboard
│   │   ├── NavItem: Project
│   │   ├── NavItem: Deploy
│   │   ├── NavItem: Logs
│   │   └── NavItem: Settings
│   └── Header
│       ├── Core Engine 상태 표시 (● 실행중)
│       └── AI Provider 상태
│
├── Dashboard
│   ├── RecentDeployments (최근 배포 목록)
│   ├── QuickActions (빠른 실행 버튼)
│   └── SystemStatus (Core Engine, Ollama 상태)
│
├── ProjectPage
│   ├── ProjectSelector
│   │   ├── [폴더 선택] 버튼 (Tauri 다이얼로그)
│   │   └── 최근 프로젝트 목록
│   └── ScanResultPanel (스캔 완료 시 표시)
│       ├── TechStackBadges (언어, 프레임워크, DB 등)
│       ├── DependencyList
│       ├── RuntimeRequirements
│       └── ActionButtons
│           ├── [Generate Docker]
│           └── [Generate CI/CD]
│
├── DeployPage
│   ├── ProjectSelector (드롭다운)
│   ├── ServerSelector (등록된 서버 목록)
│   ├── DeployConfig
│   │   ├── 배포 전략 선택
│   │   ├── Health Check URL 입력
│   │   └── Auto Rollback 토글
│   ├── [Deploy 실행] 버튼
│   └── DeployProgress (배포 중 표시)
│       ├── StepIndicator (각 단계 진행상태)
│       └── LogConsole (실시간 로그)
│
├── LogsPage
│   ├── ServerSelector
│   ├── [Collect Logs] 버튼
│   ├── LogViewer (탭: application / docker / system)
│   ├── [Analyze] 버튼
│   └── AnalysisResult
│       ├── ErrorList (탐지된 오류 목록)
│       ├── [Generate Fix] 버튼
│       └── PatchViewer (Diff 뷰어)
│           └── [Apply Fix] 버튼
│
└── SettingsPage
    ├── AIProviderSettings
    │   ├── Provider 선택 (Ollama / Claude / OpenAI)
    │   ├── Model 선택
    │   ├── Base URL (Ollama)
    │   ├── API Key (Claude / OpenAI)
    │   └── [연결 테스트] 버튼
    ├── ServerSettings
    │   ├── 등록된 서버 목록
    │   ├── [서버 추가] 버튼
    │   │   ├── Host / Port 입력
    │   │   ├── Username 입력
    │   │   ├── 인증 방식 (Key / Password)
    │   │   └── [연결 테스트] 버튼
    │   └── [서버 삭제] 버튼
    └── GeneralSettings
        ├── Core Engine 포트
        ├── Offline Mode 토글
        └── Log Level 선택
```

---

## 4. API 클라이언트 레이어

```typescript
// src/api/client.ts
const apiClient = axios.create({
    baseURL: `http://localhost:${port}/api/v1`,
    timeout: 30000,
});

// src/api/projects.ts
export const scanProject = (path: string) =>
    apiClient.post('/projects/scan', { path, use_ai: true });

export const getProject = (projectId: string) =>
    apiClient.get(`/projects/${projectId}`);

// src/api/websocket.ts
export const createDeploySocket = (deploymentId: string) =>
    new WebSocket(`ws://localhost:8765/ws/deploy/${deploymentId}`);
```

---

## 5. Zustand 상태 관리

```typescript
// src/store/projectStore.ts
interface ProjectStore {
    currentProject: ScanResult | null;
    projects: Project[];
    isScanning: boolean;
    scanProject: (path: string) => Promise<void>;
}

// src/store/deployStore.ts
interface DeployStore {
    activeDeployment: Deployment | null;
    deployHistory: Deployment[];
    deploySteps: DeployStep[];
    logs: string[];
    startDeploy: (projectId: string, serverId: string) => Promise<void>;
    appendLog: (line: string) => void;
}

// src/store/settingsStore.ts
interface SettingsStore {
    aiProvider: AIProviderConfig;
    servers: ServerConfig[];
    updateAIProvider: (config: AIProviderConfig) => Promise<void>;
    addServer: (server: ServerConfig) => Promise<void>;
}
```

---

## 6. DeployProgress 컴포넌트 상세

```typescript
// src/components/deploy/DeployProgress.tsx
// WebSocket을 통해 실시간 배포 진행상황 표시

const STEPS = ['precheck', 'build', 'upload', 'deploy', 'health_check'];

// 각 단계 상태 표시:
// pending  → 회색 원
// running  → 파란색 스피너
// success  → 초록색 체크
// failed   → 빨간색 X
// skipped  → 회색 대시

// 하단: 실시간 로그 콘솔 (최대 1000줄, 자동 스크롤)
```

---

## 7. 앱 초기화 흐름

```
앱 실행
  │
  ▼
Tauri: start_core_engine() 호출
  │
  ▼
Core Engine 포트 8765 Health Check (최대 10초 대기)
  │
  ├── 성공 → React 앱 표시
  │
  └── 실패 → "Core Engine 시작 실패" 에러 화면
              [재시도] [종료] 버튼
```

---

## 8. 빌드 및 배포

```bash
# 개발 모드
npm run tauri dev

# 프로덕션 빌드 (Core Engine 바이너리 번들 포함)
npm run tauri build

# 결과물
dist/
├── aidevops_1.0.0_x64.msi      # Windows
├── aidevops_1.0.0_aarch64.dmg  # macOS
└── aidevops_1.0.0_amd64.deb    # Linux
```

Core Engine PyInstaller 바이너리가 `src-tauri/binaries/` 에 위치해야 한다.
Tauri가 앱 실행 시 자동으로 sidecar 프로세스로 관리한다.
