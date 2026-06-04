"""
패치 제안 생성기.
분석 결과를 기반으로 파일 수정 제안(diff 형식)을 생성한다.
AI가 있으면 AI가, 없으면 룰 기반 템플릿으로 생성한다.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from aidevops.analyzer.failure_analyzer import AnalysisResult, DetectedError

logger = logging.getLogger("aidevops.patch_generator")


@dataclass
class PatchSuggestion:
    file_path: str
    description: str
    diff_content: str
    confidence: float          # 0.0 ~ 1.0


# ──────────────────────────────────────────────
# 룰 기반 패치 제안
# ──────────────────────────────────────────────

def _rule_based_patches(errors: list[DetectedError], project_path: str) -> list[PatchSuggestion]:
    suggestions: list[PatchSuggestion] = []
    proj = Path(project_path)

    for err in errors:
        if err.category == "oom":
            # docker-compose.yml 메모리 제한 제안
            compose = proj / "docker-compose.yml"
            if compose.exists():
                suggestions.append(PatchSuggestion(
                    file_path="docker-compose.yml",
                    description="OOM 방지: 컨테이너 메모리 제한 추가 제안",
                    diff_content=(
                        "--- a/docker-compose.yml\n"
                        "+++ b/docker-compose.yml\n"
                        "@@ -services > app @@\n"
                        " services:\n"
                        "   app:\n"
                        "+    deploy:\n"
                        "+      resources:\n"
                        "+        limits:\n"
                        "+          memory: 512m\n"
                        "+        reservations:\n"
                        "+          memory: 256m\n"
                    ),
                    confidence=0.7,
                ))

            # Dockerfile JVM 힙 설정 제안
            dockerfile = proj / "Dockerfile"
            if dockerfile.exists():
                suggestions.append(PatchSuggestion(
                    file_path="Dockerfile",
                    description="JVM 힙 메모리 제한 환경변수 추가 제안",
                    diff_content=(
                        "--- a/Dockerfile\n"
                        "+++ b/Dockerfile\n"
                        "@@ -CMD @@\n"
                        "-CMD [\"java\", \"-jar\", \"app.jar\"]\n"
                        "+ENV JAVA_OPTS=\"-Xms128m -Xmx256m\"\n"
                        "+CMD [\"sh\", \"-c\", \"java $JAVA_OPTS -jar app.jar\"]\n"
                    ),
                    confidence=0.6,
                ))

        elif err.category == "db_conn":
            # .env 파일 DB 설정 확인 제안
            env_file = proj / ".env"
            if env_file.exists():
                suggestions.append(PatchSuggestion(
                    file_path=".env",
                    description="DB 연결 설정 확인 필요 (host/port/credentials)",
                    diff_content=(
                        "--- a/.env\n"
                        "+++ b/.env\n"
                        "@@ -DB settings @@\n"
                        " # 아래 값들을 실제 DB 서버 정보로 수정하세요\n"
                        "+DB_HOST=localhost\n"
                        "+DB_PORT=5432\n"
                        "+DB_NAME=mydb\n"
                        "+DB_USER=myuser\n"
                        "+DB_PASSWORD=mypassword\n"
                    ),
                    confidence=0.5,
                ))

        elif err.category == "port_conflict":
            suggestions.append(PatchSuggestion(
                file_path="docker-compose.yml",
                description="포트 충돌 해결: 외부 포트 변경 제안",
                diff_content=(
                    "--- a/docker-compose.yml\n"
                    "+++ b/docker-compose.yml\n"
                    "@@ -ports @@\n"
                    "-  - \"8080:8080\"\n"
                    "+  - \"18080:8080\"  # 외부 포트를 충돌 없는 값으로 변경\n"
                ),
                confidence=0.6,
            ))

    return suggestions


# ──────────────────────────────────────────────
# AI 기반 패치 제안
# ──────────────────────────────────────────────

_AI_PATCH_PROMPT = """\
다음 배포 실패 분석 결과를 바탕으로 구체적인 파일 수정 제안을 작성하세요.

[분석 요약]
{ai_summary}

[탐지된 에러]
{detected_errors}

[프로젝트 경로]
{project_path}

아래 형식으로 최대 3개의 수정 제안을 작성하세요:

PATCH 1:
파일: <파일경로>
설명: <한 줄 설명>
신뢰도: <0.0~1.0>
diff:
--- a/<파일>
+++ b/<파일>
<unified diff 내용>

(반드시 위 형식을 지키고 JSON은 사용하지 마세요)
"""


async def _ai_patches(result: AnalysisResult, project_path: str, ai_provider) -> list[PatchSuggestion]:
    detected_text = "\n".join(
        f"- [{e.severity}] {e.name}: {e.suggestion}" for e in result.detected_errors
    )
    prompt = _AI_PATCH_PROMPT.format(
        ai_summary=result.ai_summary or "없음",
        detected_errors=detected_text or "없음",
        project_path=project_path,
    )
    try:
        raw = await ai_provider.complete(prompt)
    except Exception as exc:
        logger.warning("AI 패치 생성 실패 (무시): %s", exc)
        return []

    return _parse_ai_patches(raw)


def _parse_ai_patches(raw: str) -> list[PatchSuggestion]:
    """AI 응답에서 PATCH 블록을 파싱한다."""
    patches: list[PatchSuggestion] = []
    blocks = raw.split("PATCH ")[1:]   # "PATCH 1:", "PATCH 2:", ...

    for block in blocks:
        try:
            lines = block.strip().splitlines()
            file_path = ""
            description = ""
            confidence = 0.5
            diff_lines: list[str] = []
            in_diff = False

            for line in lines:
                if line.startswith("파일:"):
                    file_path = line.split(":", 1)[1].strip()
                elif line.startswith("설명:"):
                    description = line.split(":", 1)[1].strip()
                elif line.startswith("신뢰도:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        confidence = 0.5
                elif line.strip() == "diff:":
                    in_diff = True
                elif in_diff:
                    diff_lines.append(line)

            if file_path and diff_lines:
                patches.append(PatchSuggestion(
                    file_path=file_path,
                    description=description,
                    diff_content="\n".join(diff_lines),
                    confidence=min(max(confidence, 0.0), 1.0),
                ))
        except Exception:
            continue

    return patches


# ──────────────────────────────────────────────
# 통합 진입점
# ──────────────────────────────────────────────

async def generate_patches(
    result: AnalysisResult,
    project_path: str,
    ai_provider=None,
) -> list[PatchSuggestion]:
    """
    분석 결과를 바탕으로 패치 제안 목록을 생성한다.
    ai_provider가 있으면 AI 제안을 우선 사용하고, 없으면 룰 기반 제안을 반환한다.
    """
    if not result.has_errors:
        return []

    if ai_provider:
        patches = await _ai_patches(result, project_path, ai_provider)
        if patches:
            return patches

    return _rule_based_patches(result.detected_errors, project_path)
