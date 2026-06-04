"""
언어별 의존성 파일을 파싱하여 {name, version} 목록을 반환한다.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from aidevops.models.project import Dependency
from aidevops.scanner.file_detector import DetectedFiles


def parse(files: DetectedFiles, root: Path) -> list[Dependency]:
    """탐지된 파일 중 의존성 파일을 파싱한다."""
    if files.has("pom.xml"):
        return _parse_pom(files.path_of("pom.xml"))
    if files.has("build.gradle") or files.has("build.gradle.kts"):
        path = files.path_of("build.gradle") or files.path_of("build.gradle.kts")
        return _parse_gradle(path)
    if files.has("package.json"):
        return _parse_package_json(files.path_of("package.json"))
    if files.has("pyproject.toml"):
        return _parse_pyproject(files.path_of("pyproject.toml"))
    if files.has("requirements.txt"):
        return _parse_requirements(files.path_of("requirements.txt"))
    return []


# ── Maven ──────────────────────────────────────────────────────

def _parse_pom(path: Path) -> list[Dependency]:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}

        # 네임스페이스 유무 처리
        def find_all(tag: str):
            result = root.findall(f".//{{{ns['m']}}}{tag}")
            if not result:
                result = root.findall(f".//{tag}")
            return result

        deps = []
        for dep in find_all("dependency"):
            artifact = _text(dep, "artifactId", ns)
            version = _text(dep, "version", ns) or ""
            if artifact:
                deps.append(Dependency(name=artifact, version=version or None))
        return deps
    except Exception:
        return []


def _text(element, tag: str, ns: dict) -> str | None:
    el = element.find(f"{{{ns['m']}}}{tag}")
    if el is None:
        el = element.find(tag)
    return el.text.strip() if el is not None and el.text else None


# ── Gradle ─────────────────────────────────────────────────────

_GRADLE_DEP_RE = re.compile(
    r"""(?:implementation|api|compile|runtimeOnly|testImplementation)\s*[('"]
        (?:group:\s*['"][\w.\-]+['"]\s*,\s*name:\s*['"](?P<name1>[\w.\-]+)['"]
           |(?P<group>[\w.\-]+):(?P<name2>[\w.\-]+))
        (?::(?P<version>[\w.\-]+))?
        """,
    re.VERBOSE,
)


def _parse_gradle(path: Path) -> list[Dependency]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        deps = []
        for m in _GRADLE_DEP_RE.finditer(text):
            name = m.group("name1") or m.group("name2")
            version = m.group("version")
            if name:
                deps.append(Dependency(name=name, version=version))
        return deps
    except Exception:
        return []


# ── Node.js ────────────────────────────────────────────────────

def _parse_package_json(path: Path) -> list[Dependency]:
    import json
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        deps = []
        for section in ("dependencies", "devDependencies"):
            for name, version in data.get(section, {}).items():
                deps.append(Dependency(name=name, version=version.lstrip("^~")))
        return deps
    except Exception:
        return []


# ── Python ─────────────────────────────────────────────────────

def _parse_pyproject(path: Path) -> list[Dependency]:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        raw = data.get("project", {}).get("dependencies", [])
        # Poetry style
        if not raw:
            raw_poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            raw = [f"{k}>={v}" if isinstance(v, str) else k for k, v in raw_poetry.items()]
        return _parse_requirement_strings(raw)
    except Exception:
        return []


def _parse_requirements(path: Path) -> list[Dependency]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return _parse_requirement_strings(lines)
    except Exception:
        return []


def _parse_requirement_strings(lines: list[str]) -> list[Dependency]:
    result = []
    pattern = re.compile(r"^([A-Za-z0-9_\-]+)\s*[><=!~]+\s*([\w.\-]+)?")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = pattern.match(line)
        if m:
            result.append(Dependency(name=m.group(1), version=m.group(2)))
        else:
            name = re.split(r"[><=!~\s\[]", line)[0].strip()
            if name:
                result.append(Dependency(name=name, version=None))
    return result
