# AI DevOps Agent Platform

AI 기반 DevOps 자동화 플랫폼. 프로젝트를 분석하고 Docker/CI-CD 설정을 생성하며, SSH를 통해 배포하고 장애를 자동으로 진단합니다.

---

## 목차

- [개요](#개요)
- [아키텍처](#아키텍처)
- [주요 기능](#주요-기능)
- [사전 요구사항](#사전-요구사항)
- [설치 및 실행](#설치-및-실행)
- [Desktop App 실행](#desktop-app-실행)
- [프로젝트 구조](#프로젝트-구조)
- [API 문서](#api-문서)
- [개발 로드맵](#개발-로드맵)

---

## 개요

AI DevOps Agent Platform은 로컬에서 동작하는 DevOps 자동화 도구입니다.

- **소스코드 외부 미전송**: 분석은 전부 로컬에서 수행
- **AI Provider 선택 가능**: Ollama(기본, 무료) / Claude API / OpenAI API
- **다양한 클라이언트**: Desktop App, IntelliJ Plugin, VSCode Extension, CLI
- **Core Engine 중심 설계**: 모든 비즈니스 로직은 Core Engine(FastAPI)에 집중

---

## 아키텍처

```
[Client Layer]
  Desktop App (Tauri + React)
  IntelliJ Plugin (Kotlin)
  VSCode Extension (TypeScript)
  CLI (Python Typer)
        |
        | REST API / WebSocket
        v
[Core Engine - localhost:8765]
  Project Scanner
  Docker Generator
  CI/CD Generator
  Deployment Agent (SSH)
  Failure Analyzer
  Credential Vault (AES-256)
        |
  [AI Provider Layer]
    Ollama (기본) | Claude API | OpenAI API
        |
  [Storage]
    SQLite (aidevops.db) | Credential Vault (vault.db)
```

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **Project Scanner** | 프로젝트 폴더 분석 - 언어/프레임워크/의존성 자동 탐지 |
| **Docker Generator** | Dockerfile + docker-compose.yml 자동 생성 (멀티스테이지 빌드 포함) |
| **CI/CD Generator** | GitHub Actions / GitLab CI / Jenkins / Azure DevOps 파이프라인 생성 |
| **Deployment Agent** | SSH를 통한 Docker Compose 배포 + 자동 롤백 |
| **Failure Analyzer** | 원격 로그 수집 + 패턴/AI 기반 장애 원인 분석 |
| **Credential Vault** | SSH Key / API Key AES-256 암호화 저장 |
| **Audit Log** | 모든 작업 기록 (해시 체인 기반 변조 방지) |

---

## 사전 요구사항

### Core Engine 실행 환경

| 항목 | 요구사항 |
|------|----------|
| OS | Windows 10/11 (64-bit) |
| Python | 3.11 이상 |
| Ollama | 로컬 AI 사용 시 필요 |

**Python 설치 확인**

```powershell
python --version
# Python 3.11.x 이상이어야 함
```

**Ollama 설치** (로컬 AI 사용 시)

[https://ollama.com/download](https://ollama.com/download) 에서 Windows 설치 파일 다운로드 후 설치.

```powershell
# 모델 다운로드 (약 4GB)
ollama pull qwen2.5-coder:7b
```

### Desktop App 실행 환경

| 항목 | 요구사항 |
|------|----------|
| Node.js | 20 이상 |
| Rust | 최신 stable (rustup) |
| WebView2 | Windows 10/11 기본 내장 |
| Visual Studio C++ Build Tools | Rust 컴파일에 필요 |

```powershell
# Node.js 설치 확인
node --version   # v20.x 이상

# Rust 설치 (https://rustup.rs)
winget install Rustlang.Rustup

# 설치 후 터미널 재시작, 확인
rustc --version
cargo --version
```

> Visual Studio C++ Build Tools가 없으면 Rust 빌드가 실패합니다.
> [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 에서 설치 후
> "C++ build tools" 워크로드를 선택하세요.

### IntelliJ Plugin 개발 환경 (선택)

- IntelliJ IDEA 2023.1 이상
- JDK 17 이상
- Kotlin 플러그인 (IntelliJ 기본 내장)

---

## 설치 및 실행

### 1. 저장소 클론

```powershell
git clone <repository-url>
cd AIDevOps
```

### 2. Python 가상환경 생성 및 의존성 설치

```powershell
cd core

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (PowerShell)
.venv\Scripts\Activate.ps1

# 가상환경 활성화 (CMD)
.venv\Scripts\activate.bat

# 의존성 설치
pip install fastapi uvicorn pydantic aiosqlite paramiko cryptography
pip install jinja2 typer rich httpx pydantic-settings
```

> PowerShell에서 스크립트 실행 오류 시:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. Core Engine 실행

```powershell
# core 디렉토리에서 실행
uvicorn aidevops.main:app --host 127.0.0.1 --port 8765 --reload
```

### 4. 동작 확인

브라우저 또는 PowerShell에서:

```powershell
# Health Check
Invoke-RestMethod -Uri http://localhost:8765/health

# API 문서 (브라우저)
# http://localhost:8765/docs
```

정상 응답 예시:
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Desktop App 실행

Desktop App은 Tauri(Rust) + React로 구성되며, 실행 시 Core Engine을 자동으로 sidecar로 관리합니다.

### 1. Node.js 의존성 설치

```powershell
cd desktop
npm install
```

### 2-A. 개발 모드 실행 (핫 리로드)

> Core Engine이 별도로 실행 중이어야 합니다. ([Core Engine 실행](#3-core-engine-실행) 참고)

```powershell
# desktop 디렉토리에서
npm run tauri:dev
```

앱 창이 열리면서 `http://localhost:8765` 의 Core Engine에 자동으로 연결됩니다.

### 2-B. 프로덕션 빌드

프로덕션 빌드 시 Core Engine을 PyInstaller로 단일 바이너리로 패키징한 뒤 `src-tauri/binaries/`에 배치해야 합니다.

**Step 1. Core Engine 바이너리 생성**

```powershell
cd core

# 가상환경 활성화
.venv\Scripts\Activate.ps1

# PyInstaller 설치
pip install pyinstaller

# 단일 바이너리 생성
pyinstaller --onefile --name aidevops-core aidevops/main.py
```

빌드 완료 후 `core/dist/aidevops-core.exe` 가 생성됩니다.

**Step 2. 바이너리를 Tauri binaries 폴더에 복사**

```powershell
# Tauri는 바이너리 파일명에 타깃 트리플을 요구합니다
copy core\dist\aidevops-core.exe desktop\src-tauri\binaries\aidevops-core-x86_64-pc-windows-msvc.exe
```

**Step 3. Tauri 앱 빌드**

```powershell
cd desktop
npm run tauri:build
```

빌드 완료 후 설치 파일 위치:

```
desktop\src-tauri\target\release\bundle\
├── msi\aidevops_0.1.0_x64_en-US.msi   # Windows 설치 파일
└── nsis\aidevops_0.1.0_x64-setup.exe  # Windows 인스톨러
```

### 앱 초기화 흐름

```
앱 실행
  │
  ▼
Tauri: Core Engine sidecar 자동 실행 (포트 8765)
  │
  ▼
Health Check 대기 (최대 10초)
  │
  ├── 성공 → React UI 표시
  └── 실패 → "Core Engine 시작 실패" 오류 화면 ([재시도] [종료])
```

---

## 프로젝트 구조

```
AIDevOps/
├── core/                        # Core Engine (Python/FastAPI)
│   └── aidevops/
│       ├── main.py              # FastAPI 앱 진입점
│       ├── config.py            # 설정 관리 (Pydantic Settings)
│       ├── api/
│       │   ├── middleware.py    # CORS, 요청 로깅
│       │   └── routers/        # API 라우터
│       ├── db/
│       │   ├── database.py     # DB 연결 관리
│       │   └── migrations.py   # 테이블 초기화
│       ├── models/             # Pydantic 데이터 모델
│       ├── scanner/            # Project Scanner
│       │   ├── scanner.py
│       │   ├── file_detector.py
│       │   ├── language_detector.py
│       │   ├── dependency_parser.py
│       │   └── config_parser.py
│       ├── analyzer/           # Runtime Analyzer
│       ├── generators/
│       │   ├── docker/         # Dockerfile + Compose 생성
│       │   └── cicd/           # CI/CD 파이프라인 생성
│       ├── security/
│       │   ├── credential_vault.py  # AES-256 Credential 암호화
│       │   └── audit_logger.py      # Audit Log
│       └── ai/                 # AI Provider 추상화
│           ├── base.py
│           ├── ollama_provider.py
│           └── provider_factory.py
├── desktop/                     # Desktop App (Tauri + React)
│   ├── src/                     # React 앱
│   │   ├── api/                 # Core Engine API 클라이언트
│   │   ├── store/               # Zustand 상태 관리
│   │   ├── components/          # UI 컴포넌트
│   │   └── pages/               # ProjectPage, DeployPage, LogsPage, SettingsPage
│   ├── src-tauri/               # Tauri (Rust) 백엔드
│   │   ├── src/main.rs          # Tauri 진입점
│   │   ├── src/lib.rs           # Tauri 커맨드 (Core Engine sidecar 관리)
│   │   ├── tauri.conf.json      # Tauri 설정 (sidecar, 권한 등)
│   │   └── Cargo.toml
│   └── package.json
├── docs/                        # 설계 문서
│   ├── 01_architecture.md
│   ├── 02_module_structure.md
│   ├── 03_core_engine.md
│   ├── 04_api_spec.md
│   ├── 05_erd.md
│   ├── 06_sequence_diagrams.md
│   ├── 07_event_flow.md
│   ├── 08_plugin_structure.md
│   ├── 09_desktop_structure.md
│   └── 10_roadmap.md
└── README.md
```

---

## API 문서

Core Engine 실행 후 브라우저에서 확인:

- Swagger UI: `http://localhost:8765/docs`
- ReDoc: `http://localhost:8765/redoc`

주요 엔드포인트:

| Method | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/api/v1/projects/scan` | 프로젝트 폴더 분석 |
| POST | `/api/v1/docker/generate` | Dockerfile 생성 |
| POST | `/api/v1/cicd/generate` | CI/CD 파이프라인 생성 |
| POST | `/api/v1/deploy` | SSH 배포 실행 |
| POST | `/api/v1/analyze/failure` | 장애 분석 |
| WS | `/ws/deploy/{id}` | 배포 실시간 로그 스트림 |

상세 명세: [`docs/04_api_spec.md`](docs/04_api_spec.md)

---

## 개발 로드맵

### Phase 1 - MVP

| 단계 | 내용 | 상태 |
|------|------|------|
| Step 1-1 | Core Engine 기반 구조 (FastAPI + SQLite) | 진행 중 |
| Step 1-2 | Project Scanner | 진행 중 |
| Step 1-3 | Docker Generator | 진행 중 |
| Step 1-4 | CI/CD Generator | 진행 중 |
| Step 1-5 | Security Layer (Credential Vault) | 진행 중 |
| Step 1-6 | Deployment Agent (SSH) | 예정 |
| Step 1-7 | Failure Analyzer | 예정 |
| Step 1-8 | CLI (Typer + Rich) | 예정 |
| Step 1-9 | Desktop App (Tauri + React) | 예정 |
| Step 1-10 | IntelliJ Plugin (Kotlin) | 예정 |

### Phase 2 - 클라우드 연동

- Terraform 파일 자동 생성
- AWS / NCP / OCI / Azure 배포 지원
- 실시간 모니터링 대시보드

### Phase 3 - Self-Healing

- 장애 탐지 → 자동 분석 → 자동 수정 → 자동 재배포
- 자연어 기반 운영 명령

---

## 보안

- **소스코드 보안**: 프로젝트 파일은 로컬에서만 분석. AI 전달 시 코드 스니펫만 전송
- **Credential 암호화**: SSH Key / API Key는 AES-256(Fernet)으로 암호화하여 `vault.db`에 저장
- **Audit Log**: 모든 작업을 해시 체인으로 기록하여 변조 감지
- **Secret Masking**: 로그 출력 시 민감정보 자동 마스킹

---

## 문서

| 문서 | 내용 |
|------|------|
| [아키텍처](docs/01_architecture.md) | 전체 시스템 구조 및 기술 스택 |
| [모듈 구조](docs/02_module_structure.md) | 패키지 및 디렉토리 구조 |
| [Core Engine](docs/03_core_engine.md) | Core Engine 상세 설계 |
| [API 명세](docs/04_api_spec.md) | REST API 전체 명세 |
| [ERD](docs/05_erd.md) | 데이터베이스 스키마 |
| [시퀀스 다이어그램](docs/06_sequence_diagrams.md) | 주요 흐름 시퀀스 |
| [이벤트 흐름](docs/07_event_flow.md) | 이벤트 기반 처리 흐름 |
| [Plugin 구조](docs/08_plugin_structure.md) | IDE Plugin 설계 |
| [Desktop 구조](docs/09_desktop_structure.md) | Desktop App 설계 |
| [로드맵](docs/10_roadmap.md) | 개발 단계별 계획 |
