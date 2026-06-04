from typing import Literal
from pydantic import BaseModel


class DeployOptions(BaseModel):
    health_check_url: str | None = None       # None → 자동 추론
    health_check_timeout: int = 60
    auto_rollback: bool = True
    remote_app_dir: str | None = None         # None → /app/{project_name} 자동 설정


class DeployRequest(BaseModel):
    project_id: str
    server_id: str
    strategy: Literal["local_build", "remote_build"] = "local_build"
    options: DeployOptions = DeployOptions()


class DeployStartResponse(BaseModel):
    deployment_id: str
    status: str = "started"
    ws_url: str


class DeployStepInfo(BaseModel):
    name: str
    status: str
    duration_sec: int | None = None
    log_output: str = ""


class DeployStatusResponse(BaseModel):
    deployment_id: str
    project_id: str
    server_id: str
    status: str
    strategy: str
    steps: list[DeployStepInfo] = []
    started_at: str
    finished_at: str | None = None
    service_url: str | None = None
    error_message: str | None = None
