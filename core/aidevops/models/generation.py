from typing import Literal
from pydantic import BaseModel


class DockerOptions(BaseModel):
    multi_stage: bool = True
    include_compose: bool = True
    registry: str | None = None


class DockerGenerateRequest(BaseModel):
    project_id: str
    options: DockerOptions = DockerOptions()


class DockerGenerateResult(BaseModel):
    generation_id: str
    dockerfile: str
    docker_compose: str | None = None
    dockerignore: str
    warnings: list[str] = []


class DockerSaveRequest(BaseModel):
    generation_id: str
    project_path: str
    overwrite: bool = False


class DockerSaveResult(BaseModel):
    saved_files: list[str]
