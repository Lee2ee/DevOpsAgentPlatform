"""
ScanResult를 기반으로 Dockerfile과 .dockerignore를 생성한다.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aidevops.models.project import ScanResult

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_JINJA = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)

# 프레임워크별 기본 포트
_FRAMEWORK_PORTS: dict[str, int] = {
    "springboot": 8080,
    "quarkus": 8080,
    "micronaut": 8080,
    "jakarta-ee": 8080,
    "express": 3000,
    "fastify": 3000,
    "nestjs": 3000,
    "nextjs": 3000,
    "react": 3000,
    "vue": 3000,
    "fastapi": 8000,
    "django": 8000,
    "flask": 5000,
    "gin": 8080,
    "echo": 8080,
    "fiber": 8080,
}


def generate_dockerfile(scan: ScanResult, project_path: str | None = None) -> tuple[str, list[str]]:
    """
    Dockerfile 내용과 경고 메시지 목록을 반환한다.
    project_path: wrapper 파일(mvnw, gradlew) 존재 여부 확인용.
    """
    warnings: list[str] = []
    root = Path(project_path) if project_path else None

    lang = (scan.language or "").lower()
    fw = (scan.framework or "").lower()
    port = _FRAMEWORK_PORTS.get(fw, 8080)

    if lang in ("java", "kotlin"):
        content = _gen_java(scan, root, port, warnings)
    elif lang in ("javascript", "typescript"):
        content = _gen_node(scan, root, port, warnings)
    elif lang == "python":
        content = _gen_python(scan, root, port, warnings)
    else:
        warnings.append(f"'{lang}' 언어에 대한 Dockerfile 템플릿이 없습니다. 기본 템플릿을 생성합니다.")
        content = _gen_generic(scan, port)

    return content, warnings


def generate_dockerignore(scan: ScanResult) -> str:
    lang = (scan.language or "").lower()
    build_tool = (scan.build_tool or "").lower()

    lines = [
        "# Common",
        ".git",
        ".gitignore",
        ".env",
        ".env.*",
        "*.md",
        "",
    ]

    if lang in ("java", "kotlin"):
        lines += [
            "# Java/Kotlin",
            "target/",
            "build/",
            "*.class",
            "*.jar",
            "!.mvn/",
        ]
    elif lang in ("javascript", "typescript"):
        lines += [
            "# Node.js",
            "node_modules/",
            "dist/",
            ".next/",
            ".nuxt/",
            "coverage/",
        ]
    elif lang == "python":
        lines += [
            "# Python",
            "__pycache__/",
            "*.pyc",
            ".venv/",
            "venv/",
            "dist/",
            "*.egg-info/",
            ".pytest_cache/",
        ]

    return "\n".join(lines) + "\n"


# ── Language-specific generators ──────────────────────────────

def _gen_java(scan: ScanResult, root: Path | None, port: int, warnings: list[str]) -> str:
    java_ver = scan.language_version or "21"
    # 21 이상이면 21, 17이면 17, 그 외 21 기본
    if java_ver and java_ver.isdigit():
        java_ver = java_ver
    else:
        java_ver = "21"

    build_tool = (scan.build_tool or "maven").lower()
    has_wrapper = False
    if root:
        has_wrapper = (root / "mvnw").exists() or (root / "gradlew").exists()

    if build_tool == "gradle":
        template = _JINJA.get_template("java_gradle.j2")
    else:
        template = _JINJA.get_template("java_maven.j2")

    return template.render(
        java_version=java_ver,
        port=port,
        has_wrapper=has_wrapper,
    )


def _gen_node(scan: ScanResult, root: Path | None, port: int, warnings: list[str]) -> str:
    import json as _json

    node_ver = scan.language_version or "20"
    build_tool = (scan.build_tool or "npm").lower()
    is_typescript = (scan.language or "").lower() == "typescript"

    pkg_manager = "npm"
    if build_tool == "yarn":
        pkg_manager = "yarn"
    elif build_tool == "pnpm":
        pkg_manager = "pnpm"

    # TypeScript면 빌드 단계 기본 활성화
    has_build = is_typescript
    entry_point = "dist/index.js" if is_typescript else "index.js"

    if root and (root / "package.json").exists():
        try:
            pkg = _json.loads((root / "package.json").read_text(encoding="utf-8"))
            main = pkg.get("main", "") or ""
            scripts = pkg.get("scripts", {})
            # TypeScript면 True 유지, 아니면 build 스크립트 존재 여부로 결정
            has_build = is_typescript or ("build" in scripts)
            if is_typescript:
                entry_point = main if main.startswith("dist/") else "dist/index.js"
            else:
                entry_point = main or "index.js"
        except Exception:
            pass

    if is_typescript and not has_build:
        warnings.append("TypeScript 프로젝트인데 package.json에 'build' 스크립트가 없습니다. tsc 빌드 스크립트를 추가하세요.")

    # lock 파일 존재 여부 확인 — npm ci는 lock 파일 없으면 exit 1
    if pkg_manager == "yarn":
        has_lock = bool(root and (root / "yarn.lock").exists())
    elif pkg_manager == "pnpm":
        has_lock = bool(root and (root / "pnpm-lock.yaml").exists())
    else:
        has_lock = bool(root and (root / "package-lock.json").exists())

    if not has_lock:
        warnings.append(
            f"lock 파일({'package-lock.json' if pkg_manager == 'npm' else 'yarn.lock' if pkg_manager == 'yarn' else 'pnpm-lock.yaml'})이 없습니다. "
            "재현 가능한 빌드를 위해 lock 파일을 커밋하세요. Dockerfile은 npm install로 대체합니다."
        )

    template = _JINJA.get_template("node_npm.j2")
    return template.render(
        node_version=node_ver,
        port=port,
        pkg_manager=pkg_manager,
        entry_point=entry_point,
        has_build=has_build,
        has_lock=has_lock,
    )


def _gen_python(scan: ScanResult, root: Path | None, port: int, warnings: list[str]) -> str:
    python_ver = scan.language_version or "3.11"
    build_tool = (scan.build_tool or "pip").lower()
    framework = (scan.framework or "").lower()

    # app module 추정
    app_module = _guess_python_module(root)

    if build_tool in ("poetry", "hatch"):
        template = _JINJA.get_template("python_poetry.j2")
        return template.render(
            python_version=python_ver,
            port=port,
            framework=framework,
            app_module=app_module,
        )

    has_requirements = bool(root and (root / "requirements.txt").exists())
    pyproject_deps: list[str] = []
    if not has_requirements and root and (root / "pyproject.toml").exists():
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore
            data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
            pyproject_deps = data.get("project", {}).get("dependencies", [])
        except Exception:
            pass

    if not has_requirements and not pyproject_deps:
        warnings.append("requirements.txt가 없습니다. pip freeze > requirements.txt 실행 후 사용하세요.")

    template = _JINJA.get_template("python_pip.j2")
    return template.render(
        python_version=python_ver,
        port=port,
        framework=framework,
        app_module=app_module,
        has_requirements=has_requirements,
        pyproject_deps=pyproject_deps,
    )


def _guess_python_module(root: Path | None) -> str:
    """Python 앱의 메인 모듈명을 추정한다."""
    if root is None:
        return "main"
    # main.py, app.py, run.py 순으로 탐색
    for candidate in ("main", "app", "run", "server", "application"):
        if (root / f"{candidate}.py").exists():
            return candidate
    # src/ 하위 탐색
    for candidate in ("main", "app"):
        if (root / "src" / f"{candidate}.py").exists():
            return f"src.{candidate}"
    return "main"


def _gen_generic(scan: ScanResult, port: int) -> str:
    lang = scan.language or "unknown"
    return f"""# Generic Dockerfile for {lang}
# TODO: 해당 언어에 맞는 Dockerfile을 직접 작성하세요.
FROM ubuntu:22.04
WORKDIR /app
COPY . .
EXPOSE {port}
CMD ["echo", "애플리케이션을 실행하세요"]
"""
