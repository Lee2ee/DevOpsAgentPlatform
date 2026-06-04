from typing import Literal
from pydantic import BaseModel


class CicdOptions(BaseModel):
    deploy_target: Literal["ssh"] = "ssh"
    registry: str | None = None
    branch: str = "main"
    notify_slack: bool = False


class CicdGenerateRequest(BaseModel):
    project_id: str
    platform: Literal["github_actions", "gitlab_ci", "jenkins", "azure_devops", "bitbucket"]
    options: CicdOptions = CicdOptions()


class CicdGenerateResult(BaseModel):
    generation_id: str
    platform: str
    file_path: str
    content: str


class CicdSaveRequest(BaseModel):
    generation_id: str
    project_path: str
    overwrite: bool = False


class CicdSaveResult(BaseModel):
    saved_files: list[str]
