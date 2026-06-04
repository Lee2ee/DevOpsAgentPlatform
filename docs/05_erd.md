# AI DevOps Agent Platform - ERD / 데이터 모델

## 1. ERD 다이어그램

```
┌──────────────────┐       ┌──────────────────────┐
│    projects      │       │    project_scans      │
├──────────────────┤       ├──────────────────────┤
│ id (PK)          │──────<│ id (PK)               │
│ path             │       │ project_id (FK)       │
│ name             │       │ language              │
│ created_at       │       │ framework             │
│ updated_at       │       │ language_version      │
└──────────────────┘       │ build_tool            │
                           │ database_json         │
                           │ message_queue_json    │
                           │ cache_json            │
                           │ external_services_json│
                           │ dependencies_json     │
                           │ existing_docker       │
                           │ existing_cicd         │
                           │ scan_confidence       │
                           │ scanned_at            │
                           └──────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
          ┌─────────▼──────┐ ┌───────▼───────┐ ┌───────▼────────┐
          │  deployments   │ │  generations  │ │    analyses    │
          ├────────────────┤ ├───────────────┤ ├────────────────┤
          │ id (PK)        │ │ id (PK)       │ │ id (PK)        │
          │ project_id(FK) │ │ project_id(FK)│ │ project_id(FK) │
          │ server_id (FK) │ │ type          │ │ deployment_id  │
          │ strategy       │ │ (docker/cicd) │ │ (FK, nullable) │
          │ status         │ │ platform      │ │ severity       │
          │ trigger        │ │ content_json  │ │ error_type     │
          │ started_at     │ │ created_at    │ │ errors_json    │
          │ finished_at    │ └───────────────┘ │ analyzed_at    │
          │ service_url    │                   └────────────────┘
          └────────────────┘                          │
                  │                         ┌─────────▼──────┐
          ┌───────▼───────┐                 │    patches     │
          │ deploy_steps  │                 ├────────────────┤
          ├───────────────┤                 │ id (PK)        │
          │ id (PK)       │                 │ analysis_id(FK)│
          │ deployment_id │                 │ file_path      │
          │ (FK)          │                 │ diff_content   │
          │ name          │                 │ description    │
          │ status        │                 │ confidence     │
          │ log_output    │                 │ applied        │
          │ started_at    │                 │ applied_at     │
          │ finished_at   │                 │ created_at     │
          │ duration_sec  │                 └────────────────┘
          └───────────────┘

┌──────────────────┐       ┌──────────────────────┐
│    servers       │       │    credentials       │
├──────────────────┤       ├──────────────────────┤
│ id (PK)          │       │ id (PK)               │
│ name             │       │ key_name              │
│ host             │       │ type                  │
│ port             │       │ (ssh_key/password/    │
│ username         │       │  api_key)             │
│ auth_type        │       │ encrypted_value       │
│ credential_id(FK)│──────>│ created_at            │
│ created_at       │       │ updated_at            │
│ updated_at       │       └──────────────────────┘
└──────────────────┘

┌──────────────────────────────────────┐
│             audit_logs               │
├──────────────────────────────────────┤
│ id (PK)                              │
│ action (scan/deploy/fix/analyze/...) │
│ entity_type                          │
│ entity_id                            │
│ project_path                         │
│ target_server                        │
│ status (success/failed)              │
│ metadata_json                        │
│ performed_at                         │
│ prev_hash                            │
│ hash                                 │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│             app_config               │
├──────────────────────────────────────┤
│ key (PK)                             │
│ value_json                           │
│ updated_at                           │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│           monitoring_snapshots       │
├──────────────────────────────────────┤
│ id (PK)                              │
│ server_id (FK)                       │
│ cpu_percent                          │
│ memory_percent                       │
│ disk_percent                         │
│ network_in_mb                        │
│ network_out_mb                       │
│ collected_at                         │
└──────────────────────────────────────┘
```

---

## 2. 테이블 상세 정의

### projects
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| path | TEXT | 프로젝트 절대 경로 |
| name | TEXT | 프로젝트 이름 (경로 기반 자동 추출) |
| created_at | DATETIME | 등록 시각 |
| updated_at | DATETIME | 최종 수정 시각 |

### project_scans
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| project_id | TEXT | FK → projects.id |
| language | TEXT | 주 언어 (java, python, node, go...) |
| framework | TEXT | 프레임워크 (springboot, fastapi, express...) |
| language_version | TEXT | 언어 버전 |
| build_tool | TEXT | 빌드 도구 (maven, gradle, npm, poetry...) |
| database_json | TEXT | JSON 배열 ["oracle", "redis"] |
| message_queue_json | TEXT | JSON 배열 ["kafka"] |
| cache_json | TEXT | JSON 배열 ["redis"] |
| external_services_json | TEXT | JSON 배열 |
| dependencies_json | TEXT | JSON 배열 [{name, version}] |
| existing_docker | INTEGER | 0/1 |
| existing_cicd | TEXT | none / github_actions / gitlab / jenkins |
| scan_confidence | REAL | 0.0 ~ 1.0 |
| scanned_at | DATETIME | 분석 시각 |

### deployments
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| project_id | TEXT | FK → projects.id |
| server_id | TEXT | FK → servers.id |
| strategy | TEXT | docker_compose / docker / ssh_direct |
| status | TEXT | started / building / deploying / success / failed / rolled_back |
| trigger | TEXT | manual / auto_fix / redeploy |
| config_json | TEXT | 배포 옵션 JSON |
| started_at | DATETIME | |
| finished_at | DATETIME | |
| service_url | TEXT | 배포 후 서비스 URL |
| error_message | TEXT | 실패 시 에러 메시지 |

### deploy_steps
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| deployment_id | TEXT | FK → deployments.id |
| name | TEXT | build / upload / deploy / health_check / rollback |
| status | TEXT | pending / running / success / failed / skipped |
| log_output | TEXT | 전체 로그 출력 |
| started_at | DATETIME | |
| finished_at | DATETIME | |
| duration_sec | INTEGER | |

### servers
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| name | TEXT | 서버 식별 이름 |
| host | TEXT | IP 또는 도메인 |
| port | INTEGER | SSH 포트 (기본 22) |
| username | TEXT | SSH 사용자명 |
| auth_type | TEXT | key / password |
| credential_id | TEXT | FK → credentials.id |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### credentials
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| key_name | TEXT | 식별 이름 |
| type | TEXT | ssh_private_key / password / api_key |
| encrypted_value | TEXT | AES-256 암호화된 값 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### generations
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| project_id | TEXT | FK → projects.id |
| type | TEXT | docker / cicd |
| platform | TEXT | cicd인 경우: github_actions 등 |
| content_json | TEXT | 생성된 파일 내용 JSON |
| created_at | DATETIME | |

### analyses
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| project_id | TEXT | FK → projects.id |
| deployment_id | TEXT | FK → deployments.id (nullable) |
| severity | TEXT | critical / high / medium / low |
| error_type | TEXT | null_reference / connection_error 등 |
| errors_json | TEXT | 분석된 오류 목록 JSON |
| analyzed_at | DATETIME | |

### patches
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| analysis_id | TEXT | FK → analyses.id |
| file_path | TEXT | 수정 대상 파일 경로 |
| diff_content | TEXT | unified diff 형식 |
| description | TEXT | 수정 설명 |
| confidence | REAL | 0.0 ~ 1.0 |
| applied | INTEGER | 0/1 |
| applied_at | DATETIME | |
| created_at | DATETIME | |

### audit_logs
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT (UUID) | PK |
| action | TEXT | scan/deploy/fix/analyze/config_change 등 |
| entity_type | TEXT | project/deployment/server 등 |
| entity_id | TEXT | 대상 엔티티 ID |
| project_path | TEXT | 프로젝트 경로 |
| target_server | TEXT | 대상 서버 |
| status | TEXT | success/failed |
| metadata_json | TEXT | 추가 정보 JSON |
| performed_at | DATETIME | |
| prev_hash | TEXT | 이전 레코드 SHA256 |
| hash | TEXT | 현재 레코드 SHA256 |

### app_config
| 컬럼 | 타입 | 설명 |
|------|------|------|
| key | TEXT | PK (설정 키) |
| value_json | TEXT | 설정 값 JSON |
| updated_at | DATETIME | |

**주요 설정 키**:
- `ai_provider`: AI Provider 설정
- `server_port`: Core Engine 포트
- `offline_mode`: 오프라인 모드
- `log_level`: 로그 레벨

---

## 3. SQLite 파일 위치

```
~/.aidevops/
├── aidevops.db          # 메인 데이터베이스
└── vault.db             # Credential Vault (별도 암호화 DB)
```
