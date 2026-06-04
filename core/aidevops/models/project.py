from pydantic import BaseModel, Field


class Dependency(BaseModel):
    name: str
    version: str | None = None


class ScanResult(BaseModel):
    project_id: str
    path: str
    name: str
    language: str | None = None
    framework: str | None = None
    language_version: str | None = None
    build_tool: str | None = None
    database: list[str] = Field(default_factory=list)
    message_queue: list[str] = Field(default_factory=list)
    cache: list[str] = Field(default_factory=list)
    storage: list[str] = Field(default_factory=list)
    external_services: list[str] = Field(default_factory=list)
    existing_docker: bool = False
    existing_cicd: str = "none"
    dependencies: list[Dependency] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    scan_confidence: float = 0.0
    scanned_at: str


class ProjectSummary(BaseModel):
    project_id: str
    path: str
    name: str
    language: str | None
    framework: str | None
    scanned_at: str


class ScanRequest(BaseModel):
    path: str
    use_ai: bool = True


# ── Recommendation ─────────────────────────────────────────────

class DeployCombo(BaseModel):
    """배포 환경 + CI/CD 플랫폼의 조합 추천."""
    id: str
    deploy_name: str     # 예: "Docker Compose + VPS"
    cicd_name: str       # 예: "GitHub Actions"
    cicd_id: str         # "github_actions", "gitlab_ci", ...
    platform: str        # "docker", "aws", "oracle", "gcp", "railway"
    description: str     # 조합 전체 설명
    synergy: str         # 이 조합이 잘 맞는 이유
    pros: list[str]
    cons: list[str]
    estimated_cost: str
    complexity: str      # "simple", "moderate", "complex"
    score: int           # 1-5
    recommended: bool = False
    traffic_capacity: str = ""  # 예: "일 ~1,000명 / ~10 RPS"


class Recommendation(BaseModel):
    project_id: str
    scale: str           # "small", "medium", "large", "enterprise"
    scale_label: str
    scale_reason: str
    infra_count: int
    dep_count: int
    infra_services: list[str]
    combos: list[DeployCombo]
