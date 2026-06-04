"""
탐지된 파일과 의존성으로부터 언어, 프레임워크, 버전, 빌드 도구를 판별한다.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from aidevops.models.project import Dependency
from aidevops.scanner.file_detector import DetectedFiles


@dataclass
class LanguageInfo:
    language: str | None = None
    framework: str | None = None
    language_version: str | None = None
    build_tool: str | None = None
    confidence: float = 0.0


def detect(files: DetectedFiles, deps: list[Dependency], root: Path) -> LanguageInfo:
    dep_names = {d.name.lower() for d in deps}

    if files.has("pom.xml"):
        return _from_pom(files.path_of("pom.xml"), dep_names)
    if files.has("build.gradle") or files.has("build.gradle.kts"):
        path = files.path_of("build.gradle") or files.path_of("build.gradle.kts")
        return _from_gradle(path, dep_names)
    if files.has("package.json"):
        return _from_package_json(files.path_of("package.json"), dep_names)
    if files.has("pyproject.toml"):
        return _from_pyproject(files.path_of("pyproject.toml"), dep_names)
    if files.has("requirements.txt"):
        return _from_requirements(dep_names)
    if files.has("go.mod"):
        return _from_go_mod(files.path_of("go.mod"))
    if files.has("Cargo.toml"):
        return LanguageInfo(language="rust", build_tool="cargo", confidence=0.9)
    return LanguageInfo()


# ── Maven ──────────────────────────────────────────────────────

def _from_pom(path: Path, dep_names: set[str]) -> LanguageInfo:
    info = LanguageInfo(language="java", build_tool="maven", confidence=0.9)
    try:
        tree = ET.parse(path)
        root = tree.getroot()

        def find(tag: str) -> str | None:
            for prefix in ("", "{http://maven.apache.org/POM/4.0.0}"):
                el = root.find(f".//{prefix}{tag}")
                if el is not None and el.text:
                    return el.text.strip()
            return None

        # 언어 버전
        info.language_version = find("java.version") or find("maven.compiler.source")

        # Kotlin 탐지
        if "kotlin-stdlib" in dep_names or find("kotlin.version"):
            info.language = "kotlin"

        # 프레임워크
        info.framework = _detect_java_framework(dep_names)

        # Spring Boot 버전
        parent_artifact = find("artifactId")  # parent 섹션
        parent_version = find("version")
        if parent_artifact and "spring-boot" in parent_artifact.lower():
            info.confidence = 0.97
    except Exception:
        pass
    return info


def _detect_java_framework(dep_names: set[str]) -> str | None:
    if any("spring-boot" in d for d in dep_names):
        return "springboot"
    if any("quarkus" in d for d in dep_names):
        return "quarkus"
    if any("micronaut" in d for d in dep_names):
        return "micronaut"
    if any("jakarta" in d or "javax.servlet" in d for d in dep_names):
        return "jakarta-ee"
    return None


# ── Gradle ─────────────────────────────────────────────────────

def _from_gradle(path: Path, dep_names: set[str]) -> LanguageInfo:
    info = LanguageInfo(language="java", build_tool="gradle", confidence=0.85)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Kotlin DSL
        if path.suffix == ".kts" or "kotlin(" in text:
            info.language = "kotlin"
        # Java version
        m = re.search(r"sourceCompatibility\s*=\s*['\"]?([\d.]+)", text)
        if m:
            info.language_version = m.group(1)
        m = re.search(r"JavaVersion\.VERSION_(\w+)", text)
        if m:
            info.language_version = m.group(1).replace("_", ".")
        info.framework = _detect_java_framework(dep_names)
    except Exception:
        pass
    return info


# ── Node.js ────────────────────────────────────────────────────

def _from_package_json(path: Path, dep_names: set[str]) -> LanguageInfo:
    import json
    info = LanguageInfo(language="javascript", build_tool="npm", confidence=0.85)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        # TypeScript
        if "typescript" in dep_names or path.parent.joinpath("tsconfig.json").exists():
            info.language = "typescript"

        # Node version
        engines = data.get("engines", {})
        node_ver = engines.get("node", "")
        m = re.search(r"(\d+)", node_ver)
        if m:
            info.language_version = m.group(1)

        # 패키지 매니저
        if (path.parent / "yarn.lock").exists():
            info.build_tool = "yarn"
        elif (path.parent / "pnpm-lock.yaml").exists():
            info.build_tool = "pnpm"
        elif (path.parent / "bun.lockb").exists():
            info.build_tool = "bun"

        # 프레임워크
        info.framework = _detect_node_framework(dep_names)
        info.confidence = 0.9
    except Exception:
        pass
    return info


def _detect_node_framework(dep_names: set[str]) -> str | None:
    if "next" in dep_names:
        return "nextjs"
    if "nuxt" in dep_names:
        return "nuxt"
    if "react" in dep_names:
        return "react"
    if "vue" in dep_names:
        return "vue"
    if "express" in dep_names:
        return "express"
    if "fastify" in dep_names:
        return "fastify"
    if "nestjs" in dep_names or "@nestjs/core" in dep_names:
        return "nestjs"
    if "koa" in dep_names:
        return "koa"
    return None


# ── Python ─────────────────────────────────────────────────────

def _from_pyproject(path: Path, dep_names: set[str]) -> LanguageInfo:
    info = LanguageInfo(language="python", build_tool="pip", confidence=0.85)
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        requires = data.get("project", {}).get("requires-python", "")
        if not requires:
            requires = data.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python", "")
        m = re.search(r"(\d+\.\d+)", requires)
        if m:
            info.language_version = m.group(1)
        build_backend = data.get("build-system", {}).get("build-backend", "")
        if "poetry" in build_backend or "tool" in data and "poetry" in data["tool"]:
            info.build_tool = "poetry"
        elif "hatchling" in build_backend:
            info.build_tool = "hatch"
        elif "setuptools" in build_backend:
            info.build_tool = "setuptools"
        info.framework = _detect_python_framework(dep_names)
        info.confidence = 0.9
    except Exception:
        pass
    return info


def _from_requirements(dep_names: set[str]) -> LanguageInfo:
    return LanguageInfo(
        language="python",
        build_tool="pip",
        framework=_detect_python_framework(dep_names),
        confidence=0.8,
    )


def _detect_python_framework(dep_names: set[str]) -> str | None:
    if "fastapi" in dep_names:
        return "fastapi"
    if "django" in dep_names:
        return "django"
    if "flask" in dep_names:
        return "flask"
    if "tornado" in dep_names:
        return "tornado"
    if "aiohttp" in dep_names:
        return "aiohttp"
    return None


# ── Go ─────────────────────────────────────────────────────────

def _from_go_mod(path: Path) -> LanguageInfo:
    info = LanguageInfo(language="go", build_tool="go", confidence=0.9)
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^go\s+([\d.]+)", text, re.MULTILINE)
        if m:
            info.language_version = m.group(1)
        if "github.com/gin-gonic/gin" in text:
            info.framework = "gin"
        elif "github.com/labstack/echo" in text:
            info.framework = "echo"
        elif "github.com/gofiber/fiber" in text:
            info.framework = "fiber"
    except Exception:
        pass
    return info
