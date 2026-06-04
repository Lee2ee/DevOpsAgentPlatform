# AI DevOps Agent Platform - 모듈/패키지 구조

## 1. 전체 레포지토리 구조

```
AIDevOps/
├── docs/                          # 설계 문서
├── core/                          # Core Engine (Python)
├── desktop/                       # Desktop App (Tauri + React)
├── plugins/
│   ├── intellij/                  # IntelliJ Plugin (Kotlin)
│   └── vscode/                    # VSCode Extension (TypeScript)
├── cli/                           # CLI (Python, core 패키지 활용)
└── scripts/                       # 빌드/배포 스크립트
```

---

## 2. Core Engine 패키지 구조

```
core/
├── pyproject.toml
├── README.md
├── aidevops/                        # 메인 패키지
│   ├── __init__.py
│   ├── main.py                      # FastAPI 앱 진입점
│   ├── config.py                    # 전역 설정 (Pydantic Settings)
│   │
│   ├── api/                         # API 레이어
│   │   ├── __init__.py
│   │   ├── router.py                # 라우터 통합
│   │   ├── middleware.py            # CORS, Auth, Logging 미들웨어
│   │   └── routers/
│   │       ├── projects.py          # 프로젝트 관련 엔드포인트
│   │       ├── docker.py            # Docker 생성 엔드포인트
│   │       ├── cicd.py              # CI/CD 생성 엔드포인트
│   │       ├── deploy.py            # 배포 엔드포인트
│   │       ├── analyze.py           # 장애 분석 엔드포인트
│   │       ├── logs.py              # 로그 엔드포인트
│   │       ├── fix.py               # Auto Fix 엔드포인트
│   │       ├── monitoring.py        # 모니터링 엔드포인트
│   │       ├── config.py            # 설정 관리 엔드포인트
│   │       └── ws.py                # WebSocket 엔드포인트
│   │
│   ├── models/                      # 데이터 모델 (Pydantic)
│   │   ├── __init__.py
│   │   ├── project.py               # Project, ScanResult 모델
│   │   ├── deployment.py            # Deployment, DeployStep 모델
│   │   ├── analysis.py              # FailureAnalysis, Patch 모델
│   │   ├── infrastructure.py        # InfraRecommendation 모델
│   │   ├── monitoring.py            # MetricSnapshot, Alert 모델
│   │   └── config.py                # AIProviderConfig, ServerConfig 모델
│   │
│   ├── scanner/                     # Project Scanner
│   │   ├── __init__.py
│   │   ├── scanner.py               # 메인 스캐너 오케스트레이터
│   │   ├── file_detector.py         # 파일 기반 탐지 (pom.xml, package.json 등)
│   │   ├── language_detector.py     # 언어/프레임워크 탐지
│   │   ├── dependency_parser.py     # 의존성 파싱
│   │   ├── config_parser.py         # 설정 파일 파싱 (application.yml 등)
│   │   └── schema.py                # ScanResult JSON Schema
│   │
│   ├── analyzer/                    # 분석 컴포넌트
│   │   ├── __init__.py
│   │   ├── runtime_analyzer.py      # 런타임 요구사항 추론
│   │   ├── dependency_analyzer.py   # 의존성 분석
│   │   └── infra_planner.py         # 인프라 추천 (Rule Engine + AI)
│   │
│   ├── generators/                  # 파일 생성 컴포넌트
│   │   ├── __init__.py
│   │   ├── docker/
│   │   │   ├── __init__.py
│   │   │   ├── dockerfile_generator.py   # Dockerfile 생성
│   │   │   ├── compose_generator.py      # docker-compose.yml 생성
│   │   │   └── templates/               # Jinja2 템플릿
│   │   │       ├── java_springboot.j2
│   │   │       ├── node_express.j2
│   │   │       ├── python_fastapi.j2
│   │   │       ├── python_django.j2
│   │   │       └── compose_base.j2
│   │   └── cicd/
│   │       ├── __init__.py
│   │       ├── cicd_generator.py         # CI/CD 오케스트레이터
│   │       └── templates/
│   │           ├── github_actions.j2
│   │           ├── gitlab_ci.j2
│   │           ├── jenkinsfile.j2
│   │           └── azure_devops.j2
│   │
│   ├── agents/                      # 에이전트 컴포넌트
│   │   ├── __init__.py
│   │   ├── deployment/
│   │   │   ├── __init__.py
│   │   │   ├── deployment_agent.py   # 배포 오케스트레이터
│   │   │   ├── ssh_deployer.py       # SSH 배포
│   │   │   ├── docker_deployer.py    # Docker 배포
│   │   │   └── health_checker.py     # Health Check
│   │   ├── monitoring/
│   │   │   ├── __init__.py
│   │   │   └── monitoring_agent.py   # 메트릭 수집/이상탐지
│   │   ├── autofix/
│   │   │   ├── __init__.py
│   │   │   ├── fix_agent.py          # 수정안 생성
│   │   │   └── patch_generator.py    # Patch/Diff 생성
│   │   └── redeploy/
│   │       ├── __init__.py
│   │       └── redeploy_agent.py     # 재배포 + 자동 롤백
│   │
│   ├── collectors/                  # 데이터 수집
│   │   ├── __init__.py
│   │   ├── log_collector.py         # 로그 수집 오케스트레이터
│   │   ├── docker_log_collector.py  # Docker 로그 수집
│   │   ├── ssh_log_collector.py     # SSH 원격 로그 수집
│   │   └── failure_analyzer.py      # 로그 기반 장애 분석
│   │
│   ├── ai/                          # AI Provider 추상화
│   │   ├── __init__.py
│   │   ├── base.py                  # AIProvider ABC
│   │   ├── ollama_provider.py       # Ollama 연동
│   │   ├── claude_provider.py       # Claude API 연동
│   │   ├── openai_provider.py       # OpenAI API 연동
│   │   ├── provider_factory.py      # Provider 선택/생성
│   │   └── prompts/                 # 프롬프트 템플릿
│   │       ├── scan_analysis.txt
│   │       ├── failure_analysis.txt
│   │       ├── docker_generation.txt
│   │       └── fix_suggestion.txt
│   │
│   ├── security/                    # 보안 컴포넌트
│   │   ├── __init__.py
│   │   ├── credential_vault.py      # 자격증명 암호화 저장
│   │   ├── ssh_key_manager.py       # SSH Key 관리
│   │   ├── secret_masker.py         # 로그/응답 민감정보 마스킹
│   │   └── audit_logger.py          # Audit Log 기록
│   │
│   └── db/                          # 데이터베이스 레이어
│       ├── __init__.py
│       ├── database.py              # SQLite 연결 관리
│       ├── migrations.py            # 스키마 마이그레이션
│       └── repositories/
│           ├── project_repo.py
│           ├── deployment_repo.py
│           ├── analysis_repo.py
│           └── audit_repo.py
│
└── tests/
    ├── unit/
    │   ├── test_scanner.py
    │   ├── test_generators.py
    │   └── test_analyzers.py
    └── integration/
        ├── test_api.py
        └── test_deployment.py
```

---

## 3. Desktop App 구조

```
desktop/
├── src-tauri/                       # Tauri (Rust) 백엔드
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/
│       ├── main.rs
│       └── commands.rs              # Core Engine 프로세스 관리
│
└── src/                             # React 프론트엔드
    ├── main.tsx
    ├── App.tsx
    ├── api/                         # Core Engine API 클라이언트
    │   ├── client.ts                # Axios 기본 설정
    │   ├── projects.ts
    │   ├── deploy.ts
    │   ├── analyze.ts
    │   └── websocket.ts             # WebSocket 클라이언트
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.tsx
    │   │   └── Header.tsx
    │   ├── project/
    │   │   ├── ProjectSelector.tsx  # 폴더 선택
    │   │   └── ScanResult.tsx       # 분석 결과
    │   ├── deploy/
    │   │   ├── DeployPanel.tsx      # 배포 패널
    │   │   └── DeployProgress.tsx   # 배포 진행상황
    │   ├── logs/
    │   │   └── LogViewer.tsx        # 로그 뷰어
    │   ├── monitoring/
    │   │   └── MetricsPanel.tsx     # 메트릭 대시보드
    │   └── settings/
    │       ├── AISettings.tsx       # AI Provider 설정
    │       └── ServerSettings.tsx   # 서버 설정
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── ProjectPage.tsx
    │   ├── DeployPage.tsx
    │   ├── LogsPage.tsx
    │   └── SettingsPage.tsx
    └── store/
        ├── projectStore.ts
        ├── deployStore.ts
        └── settingsStore.ts
```

---

## 4. IntelliJ Plugin 구조

```
plugins/intellij/
├── build.gradle.kts
├── plugin.xml
└── src/main/kotlin/com/aidevops/intellij/
    ├── AiDevOpsPlugin.kt            # 플러그인 진입점
    ├── service/
    │   ├── CoreEngineService.kt     # Core Engine HTTP 클라이언트
    │   └── CoreEngineManager.kt     # Core Engine 프로세스 관리
    ├── actions/
    │   ├── AnalyzeProjectAction.kt  # AI Analyze 메뉴 액션
    │   ├── DeployAction.kt          # AI Deploy 메뉴 액션
    │   ├── GenerateDockerAction.kt  # Generate Docker 액션
    │   ├── GenerateCicdAction.kt    # Generate CI/CD 액션
    │   └── AnalyzeLogsAction.kt     # Analyze Logs 액션
    ├── toolwindow/
    │   ├── AiDevOpsToolWindow.kt    # Tool Window 패널
    │   └── DeployProgressPanel.kt  # 배포 진행 패널
    └── settings/
        └── AiDevOpsSettings.kt      # 플러그인 설정
```

---

## 5. VSCode Extension 구조

```
plugins/vscode/
├── package.json
├── tsconfig.json
└── src/
    ├── extension.ts                 # 진입점
    ├── client/
    │   └── coreEngineClient.ts      # Core Engine API 클라이언트
    ├── commands/
    │   ├── analyzeProject.ts
    │   ├── deploy.ts
    │   ├── generateDocker.ts
    │   ├── generateCicd.ts
    │   └── analyzeLogs.ts
    ├── providers/
    │   └── deployProgressProvider.ts # Tree View Provider
    └── views/
        └── deployPanel.ts           # WebView Panel
```

---

## 6. CLI 구조

```
cli/
├── pyproject.toml                   # 별도 패키지 or core 패키지 일부
└── aidevops_cli/
    ├── __init__.py
    ├── main.py                      # Typer 앱 진입점
    └── commands/
        ├── analyze.py               # aidevops analyze
        ├── deploy.py                # aidevops deploy
        ├── docker.py                # aidevops generate docker
        ├── cicd.py                  # aidevops generate cicd
        ├── logs.py                  # aidevops logs
        ├── diagnose.py              # aidevops diagnose
        └── fix.py                   # aidevops fix
```

---

## 7. 의존성 관계 다이어그램

```
CLI ──────────────────────────┐
Desktop App ──────────────────┤
IntelliJ Plugin ──────────────┤──→ Core Engine API (REST/WS)
VSCode Extension ─────────────┘         │
                                         ├── Scanner
                                         ├── Generators
                                         ├── Agents
                                         ├── Collectors
                                         ├── AI Provider
                                         ├── Security
                                         └── DB (SQLite)
```

의존성 방향: **단방향** (클라이언트 → Core Engine API)
Core Engine은 클라이언트를 직접 참조하지 않는다.
