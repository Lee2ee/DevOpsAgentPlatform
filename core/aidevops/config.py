import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI DevOps Core Engine"
    version: str = "0.1.0"

    host: str = "127.0.0.1"
    port: int = 8765

    # 데이터 디렉토리: 환경변수 AIDEVOPS_DATA_DIR 또는 기본값
    data_dir: Path = Path.home() / ".aidevops"

    log_level: str = "INFO"

    # CORS: 로컬 클라이언트만 허용
    cors_origins: list[str] = [
        "http://localhost",
        "http://localhost:1420",
        "http://127.0.0.1",
        "tauri://localhost",
    ]

    class Config:
        env_prefix = "AIDEVOPS_"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "aidevops.db"

    @property
    def vault_path(self) -> Path:
        return self.data_dir / "vault.db"

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
