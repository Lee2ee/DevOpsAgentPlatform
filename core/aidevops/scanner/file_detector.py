"""
프로젝트 디렉토리에서 알려진 구성 파일을 탐지한다.
"""

from dataclasses import dataclass, field
from pathlib import Path


# 탐지 대상 파일 (루트 기준 상대 경로 또는 glob 패턴)
_ROOT_FILES = [
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "go.mod",
    "Cargo.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "application.yml",
    "application.yaml",
    "application.properties",
    ".env",
    ".env.example",
    "README.md",
    "Jenkinsfile",
    ".gitlab-ci.yml",
]

_GLOB_PATTERNS = [
    "src/main/resources/application*.yml",
    "src/main/resources/application*.yaml",
    "src/main/resources/application*.properties",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
]

# CI/CD 매핑
_CICD_FILES = {
    "Jenkinsfile": "jenkins",
    ".gitlab-ci.yml": "gitlab_ci",
}


@dataclass
class DetectedFiles:
    found: dict[str, Path] = field(default_factory=dict)   # 파일명 → 절대경로
    github_workflows: list[Path] = field(default_factory=list)
    existing_cicd: str = "none"

    def has(self, filename: str) -> bool:
        return filename in self.found

    def path_of(self, filename: str) -> Path | None:
        return self.found.get(filename)


def detect(project_path: str | Path) -> DetectedFiles:
    """프로젝트 루트에서 알려진 파일을 탐지한다."""
    root = Path(project_path)
    result = DetectedFiles()

    # 루트 파일 직접 탐지
    for name in _ROOT_FILES:
        candidate = root / name
        if candidate.exists():
            result.found[name] = candidate
            if name in _CICD_FILES:
                result.existing_cicd = _CICD_FILES[name]

    # src/main/resources 하위 application.yml 탐지 (Spring Boot)
    for pattern in _GLOB_PATTERNS:
        for p in root.glob(pattern):
            key = p.name if "resources" in str(p) else str(p.relative_to(root))
            result.found.setdefault(key, p)

    # GitHub Actions
    gh_dir = root / ".github" / "workflows"
    if gh_dir.exists():
        result.github_workflows = list(gh_dir.glob("*.yml")) + list(gh_dir.glob("*.yaml"))
        if result.github_workflows:
            result.existing_cicd = "github_actions"

    return result
