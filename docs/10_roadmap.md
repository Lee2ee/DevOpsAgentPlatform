# AI DevOps Agent Platform - 개발 로드맵

## Phase 1: MVP (Core Engine + 기본 기능)

### Step 1-1: Core Engine 기반 구조
**목표**: FastAPI 서버 실행, DB 초기화, 기본 설정 관리

작업 목록:
- [ ] Python 프로젝트 초기화 (`pyproject.toml`, 의존성 설정)
- [ ] FastAPI 앱 기본 구조 (`main.py`, `config.py`)
- [ ] SQLite DB 초기화 + 마이그레이션 (`db/database.py`, `db/migrations.py`)
- [ ] 전체 테이블 생성 (05_erd.md 기준)
- [ ] Health Check 엔드포인트 (`GET /health`)
- [ ] 기본 미들웨어 (CORS, 요청 로깅)
- [ ] 설정 API (`GET/PUT /api/v1/config/ai`, `/config/servers`)

검증: `uvicorn aidevops.main:app --port 8765` 실행 후 `/health` 200 OK

---

### Step 1-2: Project Scanner
**목표**: 프로젝트 폴더 분석 → ScanResult JSON 생성

작업 목록:
- [ ] FileDetector: pom.xml / build.gradle / package.json / requirements.txt 탐지
- [ ] LanguageDetector: 언어/프레임워크/버전 추출
- [ ] DependencyParser: 의존성 목록 파싱
- [ ] ConfigParser: application.yml / .env / docker-compose.yml 파싱
- [ ] RuntimeAnalyzer: 외부 서비스 요구사항 추론 (Rule Engine)
- [ ] AI 보완 분석 연동 (Ollama)
- [ ] `POST /api/v1/projects/scan` API 구현
- [ ] 단위 테스트 (Java/Spring Boot, Node.js, Python 프로젝트 샘플)

검증: Spring Boot 프로젝트 스캔 → `{language: java, framework: springboot, ...}` 반환

---

### Step 1-3: Docker Generator
**목표**: ScanResult 기반 Dockerfile + docker-compose.yml 자동 생성

작업 목록:
- [ ] Jinja2 템플릿 작성 (java_springboot, node_express, python_fastapi)
- [ ] 멀티스테이지 빌드 템플릿
- [ ] docker-compose.yml 서비스 자동 구성 (DB, Redis, Kafka)
- [ ] .dockerignore 생성
- [ ] `POST /api/v1/docker/generate` API 구현
- [ ] `POST /api/v1/docker/save` API 구현

검증: Spring Boot 프로젝트 → 유효한 Dockerfile + compose 파일 생성

---

### Step 1-4: CI/CD Generator
**목표**: GitHub Actions / GitLab CI / Jenkins 파이프라인 파일 생성

작업 목록:
- [ ] GitHub Actions 템플릿 (build + docker + ssh deploy)
- [ ] GitLab CI 템플릿
- [ ] Jenkinsfile 템플릿
- [ ] `POST /api/v1/cicd/generate` API 구현
- [ ] `POST /api/v1/cicd/save` API 구현

검증: 생성된 GitHub Actions YAML이 유효한 문법인지 확인

---

### Step 1-5: Security Layer
**목표**: Credential Vault, SSH Key 관리, Secret Masking

작업 목록:
- [ ] Credential Vault (AES-256 암호화, vault.db)
- [ ] SSH Key 저장/조회
- [ ] Secret Masker (로그 출력 전 민감정보 마스킹)
- [ ] Audit Logger (모든 주요 작업 기록)
- [ ] `POST /api/v1/config/credentials` API 구현
- [ ] `POST /api/v1/config/servers` API 구현

검증: 저장된 SSH Key가 DB에 암호화 형태로 저장되는지 확인

---

### Step 1-6: Deployment Agent (SSH)
**목표**: SSH를 통한 Docker Compose 배포

작업 목록:
- [ ] SSHDeployer: Paramiko 기반 SSH 연결/명령 실행
- [ ] DeploymentAgent: 빌드 → 전송 → 배포 오케스트레이션
- [ ] HealthChecker: HTTP 헬스체크 + 타임아웃
- [ ] 자동 롤백 (이전 컨테이너 복구)
- [ ] WebSocket 실시간 이벤트 스트림
- [ ] `POST /api/v1/deploy` API 구현
- [ ] `GET /api/v1/deploy/{id}` API 구현
- [ ] `ws://localhost:8765/ws/deploy/{id}` WebSocket 구현

검증: 로컬 VM에 Spring Boot 앱 SSH 배포 성공

---

### Step 1-7: Failure Analyzer
**목표**: 로그 수집 + 패턴/AI 기반 장애 분석

작업 목록:
- [ ] SSH 원격 로그 수집 (docker logs, journalctl)
- [ ] 장애 패턴 매칭 Rule Engine (NullPointerException, Connection refused 등)
- [ ] AI 기반 장애 분석 (Ollama 연동)
- [ ] `POST /api/v1/analyze/logs/collect` API 구현
- [ ] `POST /api/v1/analyze/failure` API 구현

검증: NPE 포함 로그 → 정확한 원인 및 해결책 추론

---

### Step 1-8: CLI
**목표**: 터미널에서 Core Engine 기능 사용

작업 목록:
- [ ] Typer + Rich 기반 CLI 구조
- [ ] `aidevops analyze [경로]`
- [ ] `aidevops deploy [--server]`
- [ ] `aidevops generate docker`
- [ ] `aidevops generate cicd [--platform]`
- [ ] `aidevops diagnose [--server]`
- [ ] `aidevops logs [--server]`
- [ ] Core Engine 자동 실행 (미실행 시)

검증: `aidevops analyze .` 실행 → 스캔 결과 터미널 출력

---

### Step 1-9: Desktop App (Tauri)
**목표**: 폴더 선택 → 분석 → 배포까지 GUI 제공

작업 목록:
- [ ] Tauri 프로젝트 초기화
- [ ] Core Engine sidecar 설정
- [ ] React 앱 기본 레이아웃 (Sidebar + Header)
- [ ] ProjectPage (폴더 선택 + 스캔 결과)
- [ ] DeployPage (서버 선택 + 배포 + 실시간 로그)
- [ ] LogsPage (로그 수집 + 장애 분석 + Fix)
- [ ] SettingsPage (AI Provider + 서버 설정)

검증: Windows/macOS에서 앱 실행 → Spring Boot 프로젝트 분석 + 배포 성공

---

### Step 1-10: IntelliJ Plugin
**목표**: IntelliJ에서 우클릭으로 AI DevOps 기능 사용

작업 목록:
- [ ] IntelliJ Plugin 프로젝트 초기화
- [ ] CoreEngineService (HTTP 클라이언트)
- [ ] CoreEngineManager (자동 실행)
- [ ] 컨텍스트 메뉴 액션 (Analyze, Deploy, Generate Docker, CI/CD, Logs, Fix)
- [ ] Tool Window (Analysis / Deploy / Logs 탭)
- [ ] 배포 진행상황 WebSocket 수신

검증: IntelliJ에서 우클릭 → AI Deploy → 배포 진행 확인

---

## Phase 2: 클라우드 + 모니터링

### Step 2-1: Terraform 연동
- Terraform 파일 자동 생성 (AWS, NCP, OCI)
- Infrastructure Planner 연동

### Step 2-2: AWS 배포
- ECR Push
- ECS / EC2 배포
- IAM 권한 관리

### Step 2-3: NCP 배포
- NCP Container Registry
- NCP Server 배포

### Step 2-4: Oracle Cloud 배포
- OCI Container Registry
- OCI Compute 배포

### Step 2-5: Monitoring Agent
- CPU / Memory / Disk / Network 실시간 수집
- 이상 징후 탐지 (임계값 기반 + AI)
- 대시보드 (Desktop App Monitoring 탭)

---

## Phase 3: Self-Healing

### Step 3-1: Auto Fix Agent 고도화
- 더 복잡한 오류 패턴 처리
- 멀티파일 수정 지원
- 테스트 자동 생성 (수정 후 검증용)

### Step 3-2: Self-Healing Deployment
- 장애 탐지 → 자동 분석 → 자동 수정 → 자동 재배포 파이프라인
- 사용자 승인 레벨 설정 (자동/반자동/수동)

### Step 3-3: AI 운영 엔지니어 모드
- 자연어로 운영 명령 ("메모리가 높은데 뭐가 문제야?")
- 대화형 장애 대응

---

## 개발 우선순위 요약

```
[즉시 시작]
  Step 1-1: Core Engine 기반 구조
  Step 1-2: Project Scanner
  Step 1-3: Docker Generator

[1-1~3 완료 후]
  Step 1-4: CI/CD Generator
  Step 1-5: Security Layer

[보안 레이어 완료 후]
  Step 1-6: Deployment Agent (SSH)
  Step 1-7: Failure Analyzer

[Core 기능 완성 후]
  Step 1-8: CLI (빠른 검증용)
  Step 1-9: Desktop App
  Step 1-10: IntelliJ Plugin
```

---

## 기술 의존성 (설치 필요)

### Core Engine 개발 환경
```bash
# Python 3.11+
pip install fastapi uvicorn pydantic aiosqlite paramiko cryptography
pip install jinja2 typer rich httpx

# Ollama (로컬 AI)
# https://ollama.com/download
ollama pull qwen2.5-coder:7b
```

### Desktop App 개발 환경
```bash
# Node.js 20+, Rust (Tauri 요구사항)
npm install
cargo install tauri-cli
```

### IntelliJ Plugin 개발 환경
```
IntelliJ IDEA + Kotlin + Gradle
```
