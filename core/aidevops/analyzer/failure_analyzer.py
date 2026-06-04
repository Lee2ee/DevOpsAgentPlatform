"""
장애 분석기.

1단계: 패턴 매칭으로 알려진 에러 유형 탐지
2단계: AI(Ollama)를 통한 심층 분석 (Ollama 미사용 시 패턴 결과만 반환)
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("aidevops.failure_analyzer")


# ──────────────────────────────────────────────
# 에러 패턴 정의
# ──────────────────────────────────────────────

@dataclass
class ErrorPattern:
    name: str
    pattern: re.Pattern
    severity: str          # critical / high / medium / low
    category: str          # oom / oom_kill / db_conn / port_conflict / config / crash / timeout
    suggestion: str


_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        name="OOM Killed",
        pattern=re.compile(r"OOMKilled|Killed process|Out of memory|oom-kill", re.IGNORECASE),
        severity="critical",
        category="oom",
        suggestion="컨테이너 메모리 제한을 늘리거나 JVM 힙 크기를 조정하세요 (예: -Xmx512m → -Xmx256m).",
    ),
    ErrorPattern(
        name="Container Exit 137",
        pattern=re.compile(r"exit code.*137|exited with code 137", re.IGNORECASE),
        severity="critical",
        category="oom",
        suggestion="Exit 137은 SIGKILL을 의미합니다. OOM 또는 외부 kill로 인한 종료입니다.",
    ),
    ErrorPattern(
        name="DB Connection Refused",
        pattern=re.compile(
            r"Connection refused.*(?:3306|5432|27017|6379)|"
            r"(?:mysql|postgres|mongo|redis).*connection.*refused|"
            r"FATAL.*database.*does not exist|"
            r"Unable to acquire JDBC Connection",
            re.IGNORECASE,
        ),
        severity="high",
        category="db_conn",
        suggestion="DB 연결 정보(host/port/credentials)를 확인하고 DB 컨테이너가 실행 중인지 확인하세요.",
    ),
    ErrorPattern(
        name="Port Already in Use",
        pattern=re.compile(r"address already in use|bind.*EADDRINUSE|port.*already.*bind", re.IGNORECASE),
        severity="high",
        category="port_conflict",
        suggestion="해당 포트를 사용하는 프로세스를 종료하거나 애플리케이션 포트를 변경하세요.",
    ),
    ErrorPattern(
        name="Config / Env Missing",
        pattern=re.compile(
            r"No such file or directory.*\.(?:yml|yaml|env|properties)|"
            r"Required key.*is missing|"
            r"Environment variable.*not set|"
            r"Could not resolve placeholder|"
            r"application\.properties.*not found",
            re.IGNORECASE,
        ),
        severity="high",
        category="config",
        suggestion="필수 설정 파일 또는 환경변수가 누락되었습니다. .env 파일 또는 docker-compose 환경 설정을 확인하세요.",
    ),
    ErrorPattern(
        name="Java Heap Space",
        pattern=re.compile(r"java\.lang\.OutOfMemoryError.*Java heap space|GC overhead limit exceeded", re.IGNORECASE),
        severity="critical",
        category="oom",
        suggestion="JVM 힙 메모리 부족입니다. JAVA_OPTS에 -Xmx 값을 늘리거나 메모리 누수를 확인하세요.",
    ),
    ErrorPattern(
        name="Application Crash / Exception",
        pattern=re.compile(
            r"Exception in thread|Caused by:|"
            r"FATAL ERROR|Segmentation fault|"
            r"panic: |runtime error:",
            re.IGNORECASE,
        ),
        severity="high",
        category="crash",
        suggestion="스택 트레이스를 분석하여 근본 원인을 파악하세요.",
    ),
    ErrorPattern(
        name="Health Check Timeout",
        pattern=re.compile(r"health.*timeout|health.*unhealthy|container.*unhealthy", re.IGNORECASE),
        severity="medium",
        category="timeout",
        suggestion="애플리케이션 기동 시간이 길거나 헬스 체크 경로가 잘못되었습니다. health_check_timeout을 늘리거나 경로를 확인하세요.",
    ),
    ErrorPattern(
        name="Disk Full",
        pattern=re.compile(r"No space left on device|disk.*full|ENOSPC", re.IGNORECASE),
        severity="critical",
        category="disk",
        suggestion="서버 디스크 공간을 확보하세요. docker system prune으로 미사용 이미지를 정리할 수 있습니다.",
    ),
    ErrorPattern(
        name="Permission Denied",
        pattern=re.compile(r"Permission denied|EACCES|Access is denied", re.IGNORECASE),
        severity="medium",
        category="permission",
        suggestion="파일/디렉토리 권한을 확인하세요. 컨테이너가 non-root로 실행될 경우 볼륨 마운트 권한 문제일 수 있습니다.",
    ),
]


# ──────────────────────────────────────────────
# 분석 결과 모델
# ──────────────────────────────────────────────

@dataclass
class DetectedError:
    name: str
    severity: str
    category: str
    suggestion: str
    matched_lines: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    detected_errors: list[DetectedError] = field(default_factory=list)
    overall_severity: str = "low"
    ai_summary: str = ""
    raw_log_snippet: str = ""

    @property
    def has_errors(self) -> bool:
        return len(self.detected_errors) > 0


# ──────────────────────────────────────────────
# 패턴 매칭
# ──────────────────────────────────────────────

_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def analyze_patterns(log_text: str) -> AnalysisResult:
    """로그 텍스트에서 알려진 패턴을 탐지한다."""
    lines = log_text.splitlines()
    detected: list[DetectedError] = []

    for ep in _PATTERNS:
        matched = [l for l in lines if ep.pattern.search(l)]
        if matched:
            detected.append(DetectedError(
                name=ep.name,
                severity=ep.severity,
                category=ep.category,
                suggestion=ep.suggestion,
                matched_lines=matched[:5],   # 최대 5줄만 보관
            ))

    overall = "low"
    if detected:
        overall = max(detected, key=lambda e: _SEVERITY_ORDER.get(e.severity, 0)).severity

    # 로그 스니펫: 마지막 30줄
    snippet = "\n".join(lines[-30:]) if lines else ""

    return AnalysisResult(
        detected_errors=detected,
        overall_severity=overall,
        raw_log_snippet=snippet,
    )


# ──────────────────────────────────────────────
# AI 분석 (선택적)
# ──────────────────────────────────────────────

_AI_PROMPT_TEMPLATE = """\
다음은 배포 실패 서버의 로그입니다. 한국어로 간결하게 분석해 주세요.

[로그]
{log_snippet}

[이미 탐지된 에러]
{detected_errors}

요청사항:
1. 근본 원인 1-2문장으로 요약
2. 즉각 조치 방법 3가지 이내로 번호 목록
3. 재발 방지를 위한 권고 사항 1가지

JSON 형식이 아닌 일반 텍스트로 작성하세요.
"""


async def analyze_with_ai(result: AnalysisResult, ai_provider) -> str:
    """AI로 심층 분석 요약을 생성한다. 실패 시 빈 문자열 반환."""
    if not result.has_errors and not result.raw_log_snippet:
        return ""

    detected_text = "\n".join(
        f"- [{e.severity.upper()}] {e.name}: {e.suggestion}"
        for e in result.detected_errors
    ) or "없음"

    prompt = _AI_PROMPT_TEMPLATE.format(
        log_snippet=result.raw_log_snippet[-2000:],   # 토큰 절약
        detected_errors=detected_text,
    )

    try:
        summary = await ai_provider.complete(prompt)
        return summary.strip()
    except Exception as exc:
        logger.warning("AI 분석 실패 (무시): %s", exc)
        return ""


# ──────────────────────────────────────────────
# 통합 진입점
# ──────────────────────────────────────────────

async def analyze(log_text: str, ai_provider=None) -> AnalysisResult:
    """
    로그 텍스트를 분석하여 AnalysisResult를 반환한다.
    ai_provider가 주어지면 AI 요약도 포함한다.
    """
    result = analyze_patterns(log_text)
    if ai_provider:
        result.ai_summary = await analyze_with_ai(result, ai_provider)
    return result
