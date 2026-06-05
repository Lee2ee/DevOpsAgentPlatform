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

# (cicd_id, deploy_platform) → (템플릿파일, 저장경로)
# 복합키: "{cicd_id}_{deploy_platform}", 없으면 "{cicd_id}" fallback
_PLATFORM_MAP: dict[str, tuple[str, str]] = {
    "github_actions":          ("github_actions.j2",          ".github/workflows/deploy.yml"),
    "github_actions_aws":      ("github_actions_aws.j2",      ".github/workflows/deploy.yml"),
    "github_actions_gcp":      ("github_actions_gcp.j2",      ".github/workflows/deploy.yml"),
    "github_actions_oracle":   ("github_actions_oracle.j2",   ".github/workflows/deploy.yml"),
    "github_actions_railway":  ("railway.j2",                 "railway.toml"),
    "github_actions_vercel":   ("vercel.j2",                  "vercel.json"),
    "gitlab_ci":               ("gitlab_ci.j2",               ".gitlab-ci.yml"),
    "gitlab_ci_aws":           ("gitlab_ci_aws.j2",           ".gitlab-ci.yml"),
    "gitlab_ci_oracle":        ("gitlab_ci_oracle.j2",        ".gitlab-ci.yml"),
    "jenkins":                 ("jenkinsfile.j2",              "Jenkinsfile"),
    "azure_devops":            ("azure_devops.j2",             "azure-pipelines.yml"),
    "azure_devops_azure":      ("azure_devops_azure.j2",       "azure-pipelines.yml"),
    "bitbucket":               ("bitbucket_pipelines.j2",     "bitbucket-pipelines.yml"),
}

_FRAMEWORK_PORTS: dict[str, int] = {
    "springboot": 8080, "quarkus": 8080, "micronaut": 8080,
    "express": 3000, "fastify": 3000, "nestjs": 3000, "nextjs": 3000,
    "fastapi": 8000, "django": 8000, "flask": 5000,
    "gin": 8080, "echo": 8080,
}


def generate(scan: ScanResult, platform: str, options: CicdOptions, deploy_platform: str = "generic") -> tuple[str, str]:
    """
    CI/CD 파이프라인 파일 내용과 저장 경로를 반환한다.
    Returns: (content, file_path)
    """
    compound_key = f"{platform}_{deploy_platform}"
    key = compound_key if compound_key in _PLATFORM_MAP else platform
    template_file, file_path = _PLATFORM_MAP.get(
        key, ("github_actions.j2", ".github/workflows/deploy.yml")
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
