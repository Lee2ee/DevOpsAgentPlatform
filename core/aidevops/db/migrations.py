"""
SQLite 스키마 초기화.
테이블이 없으면 생성한다 (멱등 실행 가능).
"""

import aiosqlite

# ERD (docs/05_erd.md) 기준 전체 테이블
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_scans (
    id                      TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id),
    language                TEXT,
    framework               TEXT,
    language_version        TEXT,
    build_tool              TEXT,
    database_json           TEXT DEFAULT '[]',
    message_queue_json      TEXT DEFAULT '[]',
    cache_json              TEXT DEFAULT '[]',
    external_services_json  TEXT DEFAULT '[]',
    dependencies_json       TEXT DEFAULT '[]',
    existing_docker         INTEGER DEFAULT 0,
    existing_cicd           TEXT DEFAULT 'none',
    scan_confidence         REAL DEFAULT 0.0,
    scanned_at              DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credentials (
    id               TEXT PRIMARY KEY,
    key_name         TEXT NOT NULL UNIQUE,
    type             TEXT NOT NULL,
    encrypted_value  TEXT NOT NULL,
    created_at       DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at       DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS servers (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    host            TEXT NOT NULL,
    port            INTEGER NOT NULL DEFAULT 22,
    username        TEXT NOT NULL,
    auth_type       TEXT NOT NULL DEFAULT 'key',
    credential_id   TEXT REFERENCES credentials(id),
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deployments (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    server_id       TEXT NOT NULL REFERENCES servers(id),
    strategy        TEXT NOT NULL DEFAULT 'docker_compose',
    status          TEXT NOT NULL DEFAULT 'started',
    trigger         TEXT NOT NULL DEFAULT 'manual',
    config_json     TEXT DEFAULT '{}',
    started_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    finished_at     DATETIME,
    service_url     TEXT,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS deploy_steps (
    id              TEXT PRIMARY KEY,
    deployment_id   TEXT NOT NULL REFERENCES deployments(id),
    name            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    log_output      TEXT DEFAULT '',
    started_at      DATETIME,
    finished_at     DATETIME,
    duration_sec    INTEGER
);

CREATE TABLE IF NOT EXISTS generations (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id),
    type            TEXT NOT NULL,
    platform        TEXT,
    content_json    TEXT NOT NULL DEFAULT '{}',
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analyses (
    id              TEXT PRIMARY KEY,
    project_id      TEXT REFERENCES projects(id),
    deployment_id   TEXT REFERENCES deployments(id),
    severity        TEXT NOT NULL DEFAULT 'medium',
    error_type      TEXT,
    errors_json     TEXT NOT NULL DEFAULT '[]',
    analyzed_at     DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patches (
    id              TEXT PRIMARY KEY,
    analysis_id     TEXT NOT NULL REFERENCES analyses(id),
    file_path       TEXT NOT NULL,
    diff_content    TEXT NOT NULL,
    description     TEXT,
    confidence      REAL DEFAULT 0.0,
    applied         INTEGER DEFAULT 0,
    applied_at      DATETIME,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS monitoring_snapshots (
    id              TEXT PRIMARY KEY,
    server_id       TEXT NOT NULL REFERENCES servers(id),
    cpu_percent     REAL,
    memory_percent  REAL,
    disk_percent    REAL,
    network_in_mb   REAL,
    network_out_mb  REAL,
    collected_at    DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              TEXT PRIMARY KEY,
    action          TEXT NOT NULL,
    entity_type     TEXT,
    entity_id       TEXT,
    project_path    TEXT,
    target_server   TEXT,
    status          TEXT NOT NULL DEFAULT 'success',
    metadata_json   TEXT DEFAULT '{}',
    performed_at    DATETIME NOT NULL DEFAULT (datetime('now')),
    prev_hash       TEXT,
    hash            TEXT
);

CREATE TABLE IF NOT EXISTS app_config (
    key         TEXT PRIMARY KEY,
    value_json  TEXT NOT NULL DEFAULT '{}',
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_project_scans_project_id ON project_scans(project_id);
CREATE INDEX IF NOT EXISTS idx_deploy_steps_deployment_id ON deploy_steps(deployment_id);
CREATE INDEX IF NOT EXISTS idx_analyses_deployment_id ON analyses(deployment_id);
CREATE INDEX IF NOT EXISTS idx_patches_analysis_id ON patches(analysis_id);
CREATE INDEX IF NOT EXISTS idx_deployments_project_id ON deployments(project_id);
CREATE INDEX IF NOT EXISTS idx_deployments_server_id ON deployments(server_id);

-- 기본 AI Provider 설정 삽입 (이미 있으면 무시)
INSERT OR IGNORE INTO app_config (key, value_json)
VALUES ('ai_provider', '{"provider":"ollama","model":"qwen2.5-coder:7b","base_url":"http://localhost:11434","offline_mode":false}');

INSERT OR IGNORE INTO app_config (key, value_json)
VALUES ('general', '{"log_level":"INFO","offline_mode":false}');
"""


async def run_migrations(db: aiosqlite.Connection) -> None:
    """전체 스키마를 초기화한다. 멱등 실행 가능."""
    await db.executescript(_SCHEMA_SQL)
    await db.commit()
