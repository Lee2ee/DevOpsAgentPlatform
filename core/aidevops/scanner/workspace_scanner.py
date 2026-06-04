"""워크스페이스 루트에서 서브 프로젝트를 탐지한다."""
from dataclasses import dataclass, field
from pathlib import Path

# 빌드 파일 → 우선순위 순 (먼저 발견된 것으로 판별)
_BUILD_FILES = [
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "pom.xml",
    "build.gradle.kts",
    "build.gradle",
    "Cargo.toml",
    "go.mod",
]

_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "target", "dist", "build", ".idea", ".claude", "docs",
    ".next", ".nuxt", "coverage",
}


@dataclass
class SubProject:
    path: str
    rel_path: str   # 루트 기준 상대 경로 (예: "plugins/intellij")
    name: str       # 디렉토리 이름
    build_file: str # 탐지된 빌드 파일명


def find_subprojects(root: str, max_depth: int = 5) -> list[SubProject]:
    """루트 디렉토리에서 빌드 파일 기준으로 서브 프로젝트를 탐지한다."""
    root_path = Path(root).resolve()
    results: list[SubProject] = []

    def _walk(dir_path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            return

        filenames = {e.name for e in entries if e.is_file()}

        for bf in _BUILD_FILES:
            if bf in filenames:
                try:
                    rel = dir_path.relative_to(root_path)
                    rel_str = str(rel).replace("\\", "/")
                    if rel_str == ".":
                        rel_str = ""
                except ValueError:
                    rel_str = dir_path.name

                results.append(SubProject(
                    path=str(dir_path),
                    rel_path=rel_str,
                    name=dir_path.name,
                    build_file=bf,
                ))
                return  # 서브 프로젝트 발견 시 하위 탐색 중단

        subdirs = sorted(
            e for e in entries
            if e.is_dir() and e.name not in _SKIP_DIRS and not e.name.startswith(".")
        )
        for sub in subdirs:
            _walk(sub, depth + 1)

    _walk(root_path, 0)
    return results
