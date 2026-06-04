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
