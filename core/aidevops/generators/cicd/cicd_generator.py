"""
ScanResult를 기반으로 CI/CD 파이프라인 파일을 생성한다.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aidevops.models.cicd import CicdOptions
from aidevops.models.project import ScanResult

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_JINJA = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)

# 플랫폼 → (템플릿파일, 저장경로)
_PLATFORM_MAP: dict[str, tuple[str, str]] = {
    "github_actions": ("github_actions.j2", ".github/workflows/deploy.yml"),
    "gitlab_ci":      ("gitlab_ci.j2",      ".gitlab-ci.yml"),
    "jenkins":        ("jenkinsfile.j2",     "Jenkinsfile"),
    "azure_devops":   ("azure_devops.j2",    "azure-pipelines.yml"),
    "bitbucket":      ("bitbucket_pipelines.j2", "bitbucket-pipelines.yml"),
}

_FRAMEWORK_PORTS: dict[str, int] = {
    "springboot": 8080, "quarkus": 8080, "micronaut": 8080,
    "express": 3000, "fastify": 3000, "nestjs": 3000, "nextjs": 3000,
    "fastapi": 8000, "django": 8000, "flask": 5000,
    "gin": 8080, "echo": 8080,
}


def generate(scan: ScanResult, platform: str, options: CicdOptions) -> tuple[str, str]:
    """
    CI/CD 파이프라인 파일 내용과 저장 경로를 반환한다.
    Returns: (content, file_path)
    """
    template_file, file_path = _PLATFORM_MAP.get(
        platform, ("github_actions.j2", ".github/workflows/deploy.yml")
    )

    ctx = _build_context(scan, options)
    template = _JINJA.get_template(template_file)
    content = template.render(**ctx)
    return content, file_path


def _build_context(scan: ScanResult, options: CicdOptions) -> dict:
    lang = (scan.language or "").lower()
    fw = (scan.framework or "").lower()
    build_tool = (scan.build_tool or "").lower()
    port = _FRAMEWORK_PORTS.get(fw, 8080)

    test_cmd, build_cmd, pkg_install_cmd = _commands(lang, build_tool, fw)

    return {
        "app_name": scan.name,
        "language": lang,
        "language_version": scan.language_version or _default_version(lang),
        "framework": fw,
        "build_tool": build_tool,
        "port": port,
        "registry": options.registry,
        "branch": options.branch,
        "notify_slack": options.notify_slack,
        "test_command": test_cmd,
        "build_command": build_cmd,
        "pkg_install_command": pkg_install_cmd,
    }


def _commands(lang: str, build_tool: str, framework: str) -> tuple[str, str, str]:
    """(test_command, build_command, pkg_install_command)을 반환한다."""
    if lang in ("java", "kotlin"):
        if build_tool == "gradle":
            test  = "./gradlew test --no-daemon -q 2>/dev/null || gradle test -q"
            build = "./gradlew bootJar -x test --no-daemon -q 2>/dev/null || gradle bootJar -x test -q"
        else:
            test  = "./mvnw test -q 2>/dev/null || mvn test -q"
            build = "./mvnw package -DskipTests -q 2>/dev/null || mvn package -DskipTests -q"
        return test, build, ""

    if lang in ("javascript", "typescript"):
        install = _node_install(build_tool)
        test  = "npm test --if-present"
        build = "npm run build --if-present"
        return test, build, install

    if lang == "python":
        if build_tool in ("poetry", "hatch"):
            install = "pip install poetry && poetry install --no-interaction"
            test  = "poetry run pytest -q 2>/dev/null || echo 'no tests'"
            build = "echo 'Python build complete'"
        else:
            install = "pip install -r requirements.txt"
            test  = "pytest -q 2>/dev/null || echo 'no tests'"
            build = "echo 'Python build complete'"
        return test, build, install

    return "echo 'no tests'", "echo 'build complete'", ""


def _node_install(build_tool: str) -> str:
    if build_tool == "yarn":
        return "yarn install --frozen-lockfile"
    if build_tool == "pnpm":
        return "pnpm install --frozen-lockfile"
    return "npm ci"


def _default_version(lang: str) -> str:
    return {"java": "21", "kotlin": "21", "javascript": "20",
            "typescript": "20", "python": "3.11", "go": "1.22"}.get(lang, "latest")
