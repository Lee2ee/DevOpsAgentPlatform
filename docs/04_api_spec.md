# AI DevOps Agent Platform - REST API 명세서

## 기본 정보

- **Base URL**: `http://localhost:8765/api/v1`
- **Content-Type**: `application/json`
- **WebSocket**: `ws://localhost:8765/ws`

---

## 1. 프로젝트 분석

### POST /projects/scan
프로젝트 폴더를 분석하여 기술 스택 및 런타임 요구사항을 추출한다.

**Request**:
```json
{
  "path": "/home/user/my-spring-app",
  "use_ai": true
}
```

**Response 200**:
```json
{
  "project_id": "proj_abc123",
  "path": "/home/user/my-spring-app",
  "language": "java",
  "framework": "springboot",
  "language_version": "21",
  "build_tool": "maven",
  "database": ["oracle"],
  "message_queue": ["kafka"],
  "cache": ["redis"],
  "external_services": [],
  "existing_docker": false,
  "existing_cicd": "none",
  "dependencies": [
    {"name": "spring-boot-starter-web", "version": "3.2.0"},
    {"name": "spring-data-jpa", "version": "3.2.0"}
  ],
  "scan_confidence": 0.95,
  "scanned_at": "2026-06-01T10:00:00Z"
}
```

### GET /projects/{project_id}
저장된 프로젝트 스캔 결과를 조회한다.

**Response 200**: 위와 동일

### GET /projects
프로젝트 목록 조회.

**Response 200**:
```json
{
  "projects": [
    {"project_id": "proj_abc123", "path": "/home/user/my-spring-app", "scanned_at": "..."}
  ]
}
```

---

## 2. Docker 생성

### POST /docker/generate
ScanResult 기반으로 Dockerfile과 docker-compose.yml을 생성한다.

**Request**:
```json
{
  "project_id": "proj_abc123",
  "options": {
    "multi_stage": true,
    "include_compose": true,
    "registry": "docker.io/myuser"
  }
}
```

**Response 200**:
```json
{
  "generation_id": "gen_xyz789",
  "dockerfile": "FROM eclipse-temurin:21-jre-alpine\n...",
  "docker_compose": "version: '3.8'\nservices:\n...",
  "dockerignore": "target/\n*.log\n...",
  "warnings": ["Oracle DB는 라이선스 문제로 compose에 포함되지 않았습니다."]
}
```

### POST /docker/save
생성된 Docker 파일을 프로젝트 경로에 저장한다.

**Request**:
```json
{
  "generation_id": "gen_xyz789",
  "project_path": "/home/user/my-spring-app",
  "overwrite": false
}
```

**Response 200**:
```json
{
  "saved_files": ["Dockerfile", "docker-compose.yml", ".dockerignore"]
}
```

---

## 3. CI/CD 생성

### POST /cicd/generate
CI/CD 파이프라인 파일을 생성한다.

**Request**:
```json
{
  "project_id": "proj_abc123",
  "platform": "github_actions",
  "options": {
    "deploy_target": "ssh",
    "server_id": "srv_001",
    "registry": "ghcr.io/myuser",
    "notify_slack": false
  }
}
```

**platform 가능값**: `github_actions`, `gitlab_ci`, `jenkins`, `azure_devops`, `bitbucket`

**Response 200**:
```json
{
  "generation_id": "cicd_abc123",
  "platform": "github_actions",
  "file_path": ".github/workflows/deploy.yml",
  "content": "name: Deploy\non:\n  push:\n..."
}
```

### POST /cicd/save
생성된 파일을 프로젝트에 저장.

---

## 4. 배포

### POST /deploy
배포를 시작한다. 진행상황은 WebSocket으로 수신.

**Request**:
```json
{
  "project_id": "proj_abc123",
  "server_id": "srv_001",
  "strategy": "docker_compose",
  "options": {
    "build_local": true,
    "health_check_url": "http://{host}:8080/actuator/health",
    "health_check_timeout": 60,
    "auto_rollback": true
  }
}
```

**strategy 가능값**: `docker_compose`, `docker`, `ssh_direct`

**Response 202** (비동기 시작):
```json
{
  "deployment_id": "dep_def456",
  "status": "started",
  "ws_url": "ws://localhost:8765/ws/deploy/dep_def456"
}
```

### GET /deploy/{deployment_id}
배포 결과 조회.

**Response 200**:
```json
{
  "deployment_id": "dep_def456",
  "project_id": "proj_abc123",
  "server_id": "srv_001",
  "status": "success",
  "steps": [
    {"name": "build", "status": "success", "duration_sec": 45, "log": "..."},
    {"name": "upload", "status": "success", "duration_sec": 12},
    {"name": "deploy", "status": "success", "duration_sec": 8},
    {"name": "health_check", "status": "success", "duration_sec": 5}
  ],
  "deployed_at": "2026-06-01T10:15:00Z",
  "service_url": "http://192.168.1.100:8080"
}
```

### GET /deploy
배포 이력 목록.

### POST /deploy/{deployment_id}/rollback
수동 롤백 실행.

---

## 5. 장애 분석

### POST /analyze/failure
로그를 분석하여 장애 원인을 추론한다.

**Request**:
```json
{
  "project_id": "proj_abc123",
  "log_content": "2026-06-01 10:00:00 ERROR BookingService - ...\njava.lang.NullPointerException...",
  "log_source": "application",
  "use_ai": true
}
```

**log_source 가능값**: `application`, `docker`, `system`, `nginx`

**Response 200**:
```json
{
  "analysis_id": "ana_ghi789",
  "severity": "critical",
  "error_type": "null_reference",
  "errors": [
    {
      "type": "NullPointerException",
      "location": "BookingService.java:128",
      "cause": "reservation 객체가 null입니다",
      "fix_suggestion": "Optional<Reservation>을 사용하거나 null 체크를 추가하세요",
      "confidence": 0.92
    }
  ],
  "analyzed_at": "2026-06-01T10:20:00Z"
}
```

### POST /analyze/logs/collect
원격 서버에서 로그를 수집한다.

**Request**:
```json
{
  "server_id": "srv_001",
  "sources": ["docker", "application"],
  "lines": 500
}
```

**Response 200**:
```json
{
  "logs": {
    "docker": "...",
    "application": "..."
  }
}
```

---

## 6. Auto Fix

### POST /fix/generate
장애 분석 결과를 기반으로 코드 수정안을 생성한다.

**Request**:
```json
{
  "analysis_id": "ana_ghi789",
  "project_id": "proj_abc123"
}
```

**Response 200**:
```json
{
  "patch_id": "patch_jkl012",
  "patches": [
    {
      "file": "src/main/java/com/example/BookingService.java",
      "diff": "--- a/BookingService.java\n+++ b/BookingService.java\n...",
      "description": "Optional<Reservation> 적용으로 NPE 방지",
      "confidence": 0.88
    }
  ]
}
```

### POST /fix/apply
수정안을 프로젝트에 적용한다. (사용자 승인 필요)

**Request**:
```json
{
  "patch_id": "patch_jkl012",
  "project_path": "/home/user/my-spring-app",
  "auto_commit": false
}
```

---

## 7. 모니터링

### GET /monitoring/metrics
서버 현재 메트릭을 조회한다.

**Query Params**: `server_id=srv_001`

**Response 200**:
```json
{
  "server_id": "srv_001",
  "cpu_percent": 45.2,
  "memory_percent": 67.8,
  "disk_percent": 55.0,
  "network_in_mb": 12.3,
  "network_out_mb": 8.1,
  "collected_at": "2026-06-01T10:25:00Z"
}
```

### GET /monitoring/alerts
이상 징후 알림 목록.

---

## 8. 설정 관리

### GET /config/ai
현재 AI Provider 설정 조회.

**Response 200**:
```json
{
  "provider": "ollama",
  "model": "qwen2.5-coder:7b",
  "base_url": "http://localhost:11434",
  "offline_mode": false
}
```

### PUT /config/ai
AI Provider 설정 변경.

**Request**:
```json
{
  "provider": "ollama",
  "model": "llama3.1:8b",
  "base_url": "http://localhost:11434"
}
```

**provider 가능값**: `ollama`, `claude`, `openai`

### POST /config/servers
서버 접속 정보 등록.

**Request**:
```json
{
  "name": "prod-server-01",
  "host": "192.168.1.100",
  "port": 22,
  "username": "deploy",
  "auth_type": "key",
  "ssh_key_id": "key_001"
}
```

### GET /config/servers
등록된 서버 목록 조회.

### DELETE /config/servers/{server_id}
서버 삭제.

### POST /config/credentials
자격증명 저장.

**Request**:
```json
{
  "key": "ssh_key_prod",
  "type": "ssh_private_key",
  "value": "-----BEGIN OPENSSH PRIVATE KEY-----\n..."
}
```

---

## 9. WebSocket API

### ws://localhost:8765/ws/deploy/{deployment_id}

배포 진행상황 실시간 수신.

**이벤트 형식**:
```json
{"event": "step_start",    "step": "build",   "message": "Docker 빌드 시작"}
{"event": "step_log",      "step": "build",   "line": "[+] Building 3.5s"}
{"event": "step_complete", "step": "build",   "duration_sec": 45}
{"event": "step_start",    "step": "deploy",  "message": "원격 배포 시작"}
{"event": "step_complete", "step": "deploy",  "duration_sec": 8}
{"event": "deploy_done",   "status": "success", "url": "http://192.168.1.100:8080"}
{"event": "deploy_done",   "status": "failed",  "error": "Health check timeout"}
```

### ws://localhost:8765/ws/logs/{server_id}

실시간 로그 스트리밍.

```json
{"source": "docker", "container": "myapp", "line": "2026-06-01 INFO Starting..."}
```

---

## 10. 공통 에러 응답

```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "프로젝트를 찾을 수 없습니다",
    "details": {}
  }
}
```

**에러 코드 목록**:
| HTTP | 코드 | 설명 |
|------|------|------|
| 400 | INVALID_REQUEST | 잘못된 요청 |
| 404 | PROJECT_NOT_FOUND | 프로젝트 없음 |
| 404 | SERVER_NOT_FOUND | 서버 설정 없음 |
| 409 | DEPLOY_IN_PROGRESS | 배포 이미 진행 중 |
| 422 | SCAN_FAILED | 프로젝트 분석 실패 |
| 503 | AI_UNAVAILABLE | AI 서비스 연결 불가 |
| 503 | SSH_CONNECTION_FAILED | SSH 연결 실패 |
