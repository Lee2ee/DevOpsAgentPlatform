# AI DevOps Agent Platform - 이벤트 흐름도

## 1. 전체 라이프사이클 이벤트 흐름

```
[프로젝트 등록]
      │
      ▼
┌─────────────┐    PROJECT_SCANNED     ┌──────────────────┐
│  Project    │───────────────────────>│  ScanResult      │
│  Scanner    │                        │  저장 (DB)       │
└─────────────┘                        └──────────────────┘
      │                                         │
      │ SCAN_COMPLETE                           │
      ▼                                         ▼
┌─────────────┐                        ┌──────────────────┐
│  Docker     │                        │  CI/CD           │
│  Generator  │                        │  Generator       │
└─────────────┘                        └──────────────────┘
      │                                         │
      │ DOCKER_GENERATED                        │ CICD_GENERATED
      ▼                                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Deployment Agent                       │
│                                                         │
│  DEPLOY_STARTED → BUILD_STARTED → BUILD_COMPLETE        │
│       → TRANSFER_STARTED → TRANSFER_COMPLETE            │
│       → REMOTE_DEPLOY_STARTED → REMOTE_DEPLOY_COMPLETE  │
│       → HEALTH_CHECK_STARTED                            │
│           → HEALTH_CHECK_OK → DEPLOY_SUCCESS            │
│           → HEALTH_CHECK_FAILED → ROLLBACK_STARTED      │
│                                  → ROLLBACK_COMPLETE    │
│                                  → DEPLOY_FAILED        │
└─────────────────────────────────────────────────────────┘
      │                    │
      │ DEPLOY_SUCCESS      │ DEPLOY_FAILED
      ▼                    ▼
┌──────────┐    ┌──────────────────────┐
│Monitoring│    │   Failure Analyzer   │
│  Agent   │    │                      │
└──────────┘    │ LOGS_COLLECTED       │
      │         │ FAILURE_ANALYZED     │
      │         │ FIX_GENERATED        │
      │         │ FIX_APPLIED          │
      │         │ REDEPLOY_TRIGGERED   │
      │         └──────────────────────┘
      │                    │
      │ ANOMALY_DETECTED   │ REDEPLOY_TRIGGERED
      ▼                    ▼
┌──────────────────────────────────────┐
│           Audit Logger               │
│  (모든 이벤트 → audit_logs 기록)     │
└──────────────────────────────────────┘
```

---

## 2. 배포 이벤트 상태 전이

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ deploy() 호출
                         ▼
                    ┌─────────┐
                    │ STARTED │
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
                    │BUILDING │◄────── BUILD_LOG 이벤트 스트림
                    └────┬────┘
                         │ 빌드 성공
                    ┌────┴────┐ 빌드 실패
                    │         ├─────────────────────────────┐
                    ▼         ▼                             │
            ┌──────────┐ ┌──────────┐                      │
            │UPLOADING │ │  FAILED  │                       │
            └────┬─────┘ └──────────┘                      │
                 │ 업로드 성공                               │
            ┌────┴─────┐ 업로드 실패                        │
            │          ├─────────────────────────────┐     │
            ▼          ▼                             │     │
      ┌──────────┐ ┌──────────┐                      │     │
      │DEPLOYING │ │  FAILED  │                      │     │
      └────┬─────┘ └──────────┘                      │     │
           │ 배포 명령 성공                            │     │
      ┌────┴─────┐ 배포 실패                          │     │
      │          ├─────────────────────────────┐     │     │
      ▼          ▼                             │     │     │
┌──────────┐ ┌──────────┐                      │     │     │
│HEALTH_   │ │ROLLING   │                      │     │     │
│CHECKING  │ │  BACK    │                      │     │     │
└────┬─────┘ └────┬─────┘                      │     │     │
     │            │ 롤백 완료                   │     │     │
     │            ▼                            │     │     │
     │       ┌──────────┐                      │     │     │
     │       │ROLLED_   │                      │     │     │
     │       │  BACK    │                      │     │     │
     │       └──────────┘                      │     │     │
     │                                         ▼     ▼     ▼
     │ 헬스체크 실패 → auto_rollback=true   ┌──────────────┐
     │────────────────────────────────────> │    FAILED    │
     │                                      └──────────────┘
     │ 헬스체크 성공
     ▼
┌──────────┐
│ SUCCESS  │
└──────────┘
```

---

## 3. WebSocket 이벤트 스키마

배포 진행 중 클라이언트로 전송되는 모든 이벤트:

```
EVENT: deploy_started
{
  "event": "deploy_started",
  "deployment_id": "dep_xxx",
  "project": "my-spring-app",
  "server": "prod-server-01",
  "timestamp": "2026-06-01T10:00:00Z"
}

EVENT: step_started
{
  "event": "step_started",
  "step": "build",            # build | upload | deploy | health_check | rollback
  "message": "Docker 이미지 빌드 시작",
  "timestamp": "..."
}

EVENT: step_log
{
  "event": "step_log",
  "step": "build",
  "line": "[+] Building 12.3s (8/8) FINISHED",
  "timestamp": "..."
}

EVENT: step_completed
{
  "event": "step_completed",
  "step": "build",
  "status": "success",        # success | failed
  "duration_sec": 45,
  "timestamp": "..."
}

EVENT: deploy_completed
{
  "event": "deploy_completed",
  "status": "success",        # success | failed | rolled_back
  "service_url": "http://192.168.1.100:8080",
  "total_duration_sec": 78,
  "timestamp": "..."
}

EVENT: rollback_started
{
  "event": "rollback_started",
  "reason": "health_check_timeout",
  "timestamp": "..."
}
```

---

## 4. 장애 감지 → 자동 분석 흐름

```
[Monitoring Agent]
       │
       │  메트릭 수집 (30초 간격)
       ▼
  ┌────────────┐
  │ CPU > 90%  │──→ ANOMALY_DETECTED (cpu_high)
  │ Mem > 85%  │──→ ANOMALY_DETECTED (memory_high)
  │ Error rate │──→ ANOMALY_DETECTED (error_rate_spike)
  │  급증      │
  └────────────┘
       │
       ▼
  [Log Collector 자동 트리거]
       │
       ▼
  [Failure Analyzer 자동 실행]
       │
       ├── Rule 패턴 매칭
       │
       └── AI 분석 (Ollama)
              │
              ▼
       [Alert 생성 + UI 알림]
              │
              ▼ (사용자 승인 후)
       [Auto Fix Agent]
              │
              ▼
       [사용자 Patch 검토 + 승인]
              │
              ▼
       [ReDeploy Agent]
```

---

## 5. AI Provider 이벤트 흐름

```
Core Engine 내부 AI 호출

analyze(prompt) 호출
      │
      ▼
[ProviderFactory.get_provider()]
      │
      ├── provider_config.provider == "ollama"
      │         │
      │         ▼
      │   [OllamaProvider.complete()]
      │         │
      │         ├── Ollama 응답 성공 → 결과 반환
      │         │
      │         └── Ollama 연결 실패
      │                   │
      │                   ├── offline_mode == True
      │                   │         → Rule Engine Fallback
      │                   │
      │                   └── offline_mode == False
      │                             → AI_UNAVAILABLE 에러
      │
      ├── provider_config.provider == "claude"
      │         │
      │         ▼
      │   [ClaudeProvider.complete()]
      │         → Anthropic API 호출
      │
      └── provider_config.provider == "openai"
                │
                ▼
          [OpenAIProvider.complete()]
                → OpenAI API 호출

결과 반환 전: SecretMasker.mask(result) 적용
```

---

## 6. 데이터 흐름 요약

```
[입력]                  [처리]                  [출력]
프로젝트 경로 ──────→ ProjectScanner ──────→ ScanResult JSON
ScanResult   ──────→ DockerGenerator ──────→ Dockerfile + compose
ScanResult   ──────→ CicdGenerator   ──────→ CI/CD YAML
배포 요청    ──────→ DeploymentAgent  ──────→ 배포 결과 + 상태 이벤트
서버 로그    ──────→ FailureAnalyzer  ──────→ 장애 분석 보고서
장애 분석    ──────→ AutoFixAgent     ──────→ Patch (Unified Diff)
Patch 적용   ──────→ ReDeployAgent    ──────→ 재배포 + 롤백
```
