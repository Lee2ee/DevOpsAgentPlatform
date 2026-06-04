# AI DevOps Agent Platform - 전체 아키텍처 설계서

## 1. 아키텍처 개요

### 핵심 원칙
- **Core Engine 중심 구조**: 모든 비즈니스 로직은 Core Engine에 집중
- **클라이언트는 UI만 담당**: Desktop, Plugin, CLI는 Core Engine API를 호출하는 thin client
- **로컬 우선 보안**: 소스코드는 외부 서버로 전송하지 않음
- **AI Provider 추상화**: Ollama(기본) 포함 다양한 AI 모델 선택 가능

---

## 2. 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────┐  ┌─────────┐  │
│  │ Desktop App  │  │ IntelliJ     │  │ VSCode │  │   CLI   │  │
│  │ (Tauri+React)│  │   Plugin     │  │  Ext.  │  │(Python) │  │
│  └──────┬───────┘  └──────┬───────┘  └───┬────┘  └────┬────┘  │
└─────────┼─────────────────┼──────────────┼─────────────┼───────┘
          │                 │              │             │
          └─────────────────┴──────────────┴─────────────┘
                                   │
                          REST API / WebSocket
                                   │
┌──────────────────────────────────▼──────────────────────────────┐
│                    Core Engine (Python/FastAPI)                  │
│                     localhost:8765                               │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Project   │  │   Runtime    │  │   Dependency         │  │
│  │   Scanner   │  │   Analyzer   │  │   Analyzer           │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Docker    │  │   CI/CD      │  │  Infrastructure      │  │
│  │  Generator  │  │  Generator   │  │    Planner           │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Deployment  │  │     Log      │  │   Failure            │  │
│  │    Agent    │  │  Collector   │  │   Analyzer           │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Monitoring  │  │  Auto Fix    │  │   ReDeploy           │  │
│  │    Agent    │  │    Agent     │  │    Agent             │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  AI Provider Layer                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │  │
│  │  │  Ollama  │  │  Claude  │  │  OpenAI  │  │ Custom  │  │  │
│  │  │ (기본)   │  │   API    │  │   API    │  │ Model   │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Security & Storage Layer                    │  │
│  │  ┌───────────┐  ┌──────────────┐  ┌───────────────────┐  │  │
│  │  │ Cred.Vault│  │  Audit Log   │  │  SQLite (local)   │  │  │
│  │  └───────────┘  └──────────────┘  └───────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                                │
   ┌──────▼──────┐                 ┌───────▼──────┐
   │  SSH Target  │                 │  Container   │
   │   Servers    │                 │  Registry    │
   └─────────────┘                 └──────────────┘
```

---

## 3. Core Engine 통신 방식

| 인터페이스 | 프로토콜 | 용도 |
|------------|----------|------|
| REST API   | HTTP/JSON | 분석, 생성, 조회 요청 |
| WebSocket  | WS | 배포 진행상황 실시간 스트림 |
| Server-Sent Events | SSE | 로그 스트리밍, 모니터링 |

### Core Engine 기동 방식
- **Desktop App**: Tauri가 Core Engine 프로세스를 sidecar로 실행
- **IntelliJ / VSCode Plugin**: 플러그인이 Core Engine 설치 여부 확인 후 자동 실행
- **CLI**: Core Engine과 동일 프로세스 또는 별도 서버에 연결
- **기본 포트**: 8765 (설정 변경 가능)

---

## 4. 기술 스택

### Core Engine
| 항목 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| API 서버 | FastAPI + Uvicorn |
| AI 연동 | Ollama (기본), Anthropic SDK, OpenAI SDK |
| 로컬 DB | SQLite (aiosqlite) |
| 스키마 검증 | Pydantic v2 |
| SSH 연결 | Paramiko / asyncssh |
| 설정 관리 | Pydantic Settings |
| 암호화 | cryptography (Fernet) |
| 패키징 | PyInstaller (단일 바이너리) |

### Desktop Application
| 항목 | 기술 |
|------|------|
| 프레임워크 | Tauri 2.x |
| UI | React 18 + TypeScript |
| 상태관리 | Zustand |
| UI 컴포넌트 | shadcn/ui + Tailwind CSS |
| 빌드 | Vite |
| API 클라이언트 | Axios + React Query |

### IDE Plugins
| 항목 | 기술 |
|------|------|
| IntelliJ | Kotlin + IntelliJ Platform SDK |
| VSCode | TypeScript + VS Code Extension API |
| 공통 | Core Engine REST API 호출 |

### CLI
| 항목 | 기술 |
|------|------|
| 언어 | Python (Core Engine 패키지 일부) |
| 프레임워크 | Typer |
| 출력 포맷 | Rich |

---

## 5. 배포 모델

```
[사용자 로컬 머신]
  ├── Core Engine (FastAPI 서버, 포트 8765)
  ├── Desktop App (Tauri)
  ├── CLI (aidevops 커맨드)
  └── IDE Plugin (Core Engine API 호출)

[분석/배포 대상]
  ├── 로컬 프로젝트 폴더 (직접 접근)
  ├── SSH 원격 서버
  ├── Docker Registry (선택)
  └── Cloud (AWS/NCP/OCI/Azure/GCP - Phase 2)
```

---

## 6. 보안 아키텍처

```
[민감 데이터 흐름]
  SSH Key / API Key / Password
    → AES-256 암호화 (Fernet)
    → Credential Vault (로컬 SQLite, 암호화 파티션)
    → 메모리 내에서만 복호화 사용
    → 로그/응답에서 자동 마스킹

[소스코드 보안]
  프로젝트 파일 → 로컬 분석만 수행
  AI에 전달 시 → 코드 스니펫만, 전체 파일 미전송 (설정 가능)
  Offline Mode → AI 없이 Rule 기반 분석만 수행

[Audit Log]
  모든 작업(분석/배포/수정) → 로컬 SQLite audit_log 테이블 기록
  변조 방지 → 해시 체인 (prev_hash 포함)
```

---

## 7. 확장성 설계 (Plugin Architecture)

Core Engine 내부 각 컴포넌트는 인터페이스 기반으로 설계되어 확장 가능:

```python
# 예시: AI Provider 확장
class AIProvider(ABC):
    async def analyze(self, prompt: str, context: dict) -> str: ...

class OllamaProvider(AIProvider): ...
class ClaudeProvider(AIProvider): ...
class CustomProvider(AIProvider): ...
```

```python
# 예시: Deployment Target 확장
class DeploymentTarget(ABC):
    async def deploy(self, artifact: Artifact, config: DeployConfig) -> DeployResult: ...

class SSHTarget(DeploymentTarget): ...
class DockerTarget(DeploymentTarget): ...
class KubernetesTarget(DeploymentTarget): ...  # Phase 2
```
