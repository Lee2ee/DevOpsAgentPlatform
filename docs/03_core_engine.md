# AI DevOps Agent Platform - Core Engine 상세 설계

## 1. Core Engine 개요

Core Engine은 FastAPI 기반 로컬 HTTP 서버로 실행된다.
모든 클라이언트(Desktop, Plugin, CLI)는 이 서버의 REST API와 WebSocket을 통해 통신한다.

- **기본 포트**: 8765
- **프로토콜**: HTTP/1.1, WebSocket
- **데이터 형식**: JSON
- **인증**: localhost 토큰 (설정 가능, 기본 비활성)

---

## 2. 각 컴포넌트 상세 설계

### 2.1 Project Scanner

**역할**: 프로젝트 폴더를 분석하여 기술 스택, 런타임 요구사항, 의존성을 추출한다.

**처리 흐름**:
```
프로젝트 경로 입력
    ↓
FileDetector: 주요 파일 탐지 (pom.xml, package.json, etc.)
    ↓
LanguageDetector: 언어/프레임워크 식별
    ↓
DependencyParser: 의존성 목록 추출
    ↓
ConfigParser: 설정 파일 분석 (application.yml, .env 등)
    ↓
RuntimeAnalyzer: 외부 서비스 요구사항 추론
    ↓
AI 보완 분석 (Ollama): README.md, 코드 패턴 기반 추가 추론
    ↓
ScanResult JSON 반환
```

**탐지 가능 기술 스택**:
| 파일 | 탐지 항목 |
|------|-----------|
| pom.xml | Java/Kotlin, Spring Boot, 의존성 |
| build.gradle | Java/Kotlin, 의존성 |
| package.json | Node.js, React/Vue/Next.js, 의존성 |
| requirements.txt / pyproject.toml | Python, FastAPI/Django/Flask |
| go.mod | Go, Gin/Echo |
| Cargo.toml | Rust |
| Dockerfile | 이미 존재하는 컨테이너 설정 |
| docker-compose.yml | 서비스 구성 |
| application.yml / .properties | DB, Cache, MQ 설정 |
| .env | 환경변수, DB URL |

**ScanResult 스키마**:
```json
{
  "project_id": "uuid",
  "path": "/path/to/project",
  "language": "java",
  "framework": "springboot",
  "language_version": "21",
  "build_tool": "maven",
  "database": ["oracle", "redis"],
  "message_queue": ["kafka"],
  "cache": ["redis"],
  "storage": [],
  "external_services": ["elasticsearch"],
  "existing_docker": false,
  "existing_cicd": "none",
  "dependencies": [{"name": "spring-boot-starter-web", "version": "3.2.0"}],
  "config_files": ["application.yml", ".env"],
  "scan_confidence": 0.95,
  "scanned_at": "2026-06-01T00:00:00Z"
}
```

---

### 2.2 Docker Generator

**역할**: ScanResult를 기반으로 최적화된 Dockerfile과 docker-compose.yml을 생성한다.

**생성 전략**:
- 멀티스테이지 빌드 (빌드 이미지 / 런타임 이미지 분리)
- 언어별 최적 베이스 이미지 선택
- 비root 사용자 실행
- 헬스체크 포함
- .dockerignore 자동 생성

**템플릿 매핑**:
```
language=java, framework=springboot  → java_springboot.j2
language=node, framework=express     → node_express.j2
language=node, framework=nextjs      → node_nextjs.j2
language=python, framework=fastapi   → python_fastapi.j2
language=python, framework=django    → python_django.j2
language=go                          → go_gin.j2
```

**docker-compose.yml 생성 규칙**:
- ScanResult.database, message_queue, cache에 따라 서비스 자동 추가
- 예: database=["redis"] → compose에 redis 서비스 포함
- 예: database=["oracle"] → oracle 또는 대체 DB 서비스 포함 (oracle은 라이선스 주의 메시지 포함)
- 볼륨, 네트워크, 환경변수 템플릿 자동 구성

---

### 2.3 CI/CD Generator

**역할**: 프로젝트 분석 결과와 선택된 플랫폼에 맞는 CI/CD 파이프라인 파일을 생성한다.

**생성 파일**:
| 플랫폼 | 파일 경로 |
|--------|-----------|
| GitHub Actions | .github/workflows/deploy.yml |
| GitLab CI | .gitlab-ci.yml |
| Jenkins | Jenkinsfile |
| Azure DevOps | azure-pipelines.yml |
| Bitbucket | bitbucket-pipelines.yml |

**파이프라인 단계 (공통)**:
```
1. Checkout
2. Setup (언어별 런타임 설치)
3. Test (테스트 실행)
4. Build (빌드)
5. Docker Build & Push
6. Deploy (SSH or Cloud)
7. Health Check
8. Notify (Slack/이메일 - 선택)
```

---

### 2.4 Infrastructure Planner

**역할**: 프로젝트 요구사항과 사용자 입력(예상 트래픽, 예산, 보안요구)을 기반으로 인프라를 추천한다.

**판단 방식**: Rule Engine 우선, AI 보완

**Rule Engine 예시**:
```python
if expected_users < 1000 and budget < 50000:
    recommend("single_server", "NCP micro", "AWS t3.small")
if expected_users > 100000:
    recommend("ha_cluster", load_balancer=True, auto_scaling=True)
if security_level == "enterprise":
    recommend("private_network", vpn=True, waf=True)
```

**출력**:
```json
{
  "recommended_provider": "AWS",
  "instance_type": "t3.medium",
  "estimated_monthly_cost_krw": 80000,
  "high_availability": false,
  "load_balancer": false,
  "cache_required": true,
  "alternatives": [
    {"provider": "NCP", "type": "c2-g3", "cost_krw": 60000},
    {"provider": "OCI", "type": "VM.Standard.E4.Flex", "cost_krw": 45000}
  ]
}
```

---

### 2.5 Deployment Agent

**역할**: 빌드 → 컨테이너화 → 업로드 → 배포 → 헬스체크 → 롤백 전체 파이프라인 실행

**배포 흐름**:
```
Deploy 요청
    ↓
PreDeployCheck (서버 접속 확인, 디스크 여유공간 확인)
    ↓
Build (로컬 Docker 빌드 또는 원격 빌드)
    ↓
Push (Container Registry 업로드 - 설정된 경우)
    ↓
RemoteDeploy
    ├── SSH: docker pull + docker-compose up
    └── Direct SSH: 파일 전송 + 실행
    ↓
HealthCheck (HTTP /health or /actuator/health)
    ├── 성공 → 배포 완료
    └── 실패 → 자동 롤백 (이전 컨테이너 복구)
    ↓
DeployResult 반환 + WebSocket 실시간 이벤트 스트림
```

**배포 상태 이벤트** (WebSocket):
```json
{"event": "deploy_step", "step": "build", "status": "running", "message": "Docker 빌드 중..."}
{"event": "deploy_step", "step": "build", "status": "done", "message": "빌드 완료 (12s)"}
{"event": "deploy_step", "step": "deploy", "status": "running", "message": "원격 서버에 배포 중..."}
{"event": "deploy_complete", "status": "success", "url": "http://server:8080"}
```

---

### 2.6 Failure Analyzer

**역할**: 수집된 로그를 분석하여 장애 원인을 추론하고 해결책을 제안한다.

**분석 방식**:
1. **패턴 매칭** (Rule Engine): 알려진 오류 패턴 빠른 탐지
2. **AI 분석** (Ollama): 복잡한 오류, 알 수 없는 패턴

**알려진 패턴 예시**:
```python
PATTERNS = [
    {
        "pattern": r"NullPointerException",
        "category": "null_reference",
        "cause_template": "{file}:{line} - Null 참조",
        "fix_template": "Optional.ofNullable() 또는 null 체크 추가"
    },
    {
        "pattern": r"Connection refused.*:(\d+)",
        "category": "connection_error",
        "cause_template": "포트 {port} 연결 실패",
        "fix_template": "서비스 실행 여부 및 방화벽 설정 확인"
    },
    {
        "pattern": r"ORA-(\d{5})",
        "category": "oracle_error",
        "fix_template": "Oracle 오류코드 {code} 참조"
    }
]
```

**출력**:
```json
{
  "analysis_id": "uuid",
  "severity": "critical",
  "error_type": "null_reference",
  "location": "BookingService.java:128",
  "cause": "reservation 객체가 null입니다",
  "fix_suggestion": "Optional<Reservation>으로 변환하거나 null 체크를 추가하세요",
  "code_snippet": "...",
  "confidence": 0.92
}
```

---

### 2.7 AI Provider Layer

**역할**: 다양한 AI 모델을 동일한 인터페이스로 추상화한다.

```python
class AIProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

**Ollama 연동**:
- 기본 모델: `qwen2.5-coder:7b` (코드 분석 특화)
- 대안 모델: `llama3.1:8b`, `deepseek-coder-v2:16b`
- Ollama API: `http://localhost:11434/api/generate`

**Fallback 전략**:
```
Ollama (기본)
    → 실패 시 → Rule Engine 기반 분석으로 대체
    → Offline Mode: AI 없이 Rule Engine만 사용
```

**프롬프트 관리**:
- 프롬프트 템플릿은 `ai/prompts/` 디렉토리에 분리 저장
- 코드 전체 전송 금지, 관련 스니펫만 전달 (보안)
- 민감정보 마스킹 후 AI 전달

---

### 2.8 Credential Vault

**역할**: SSH Key, API Key, 서버 비밀번호 등 민감 자격증명을 안전하게 저장/조회한다.

**암호화 방식**:
- 마스터 키: OS Keychain (keyring 라이브러리) 또는 파생 키
- 데이터 암호화: AES-256 (Fernet)
- 저장소: 로컬 SQLite (`~/.aidevops/vault.db`)

```python
class CredentialVault:
    def store(self, key: str, value: str) -> None: ...
    def retrieve(self, key: str) -> str: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self) -> list[str]: ...
```

---

### 2.9 Audit Logger

**역할**: 모든 작업을 추적 가능한 로그로 기록한다.

**기록 항목**:
- 작업 종류 (scan, deploy, fix, analyze)
- 대상 프로젝트/서버
- 수행 시각
- 수행 결과
- 이전 레코드 해시 (변조 방지)

```json
{
  "id": "uuid",
  "action": "deploy",
  "project_path": "/home/user/myapp",
  "target_server": "192.168.1.100",
  "status": "success",
  "performed_at": "2026-06-01T10:00:00Z",
  "prev_hash": "sha256:...",
  "hash": "sha256:..."
}
```
