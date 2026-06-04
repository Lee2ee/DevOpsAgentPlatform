"""
Project Scanner 오케스트레이터.

흐름:
  1. FileDetector → 파일 목록
  2. DependencyParser → 의존성 목록
  3. LanguageDetector → 언어/프레임워크
  4. ConfigParser → 설정 기반 서비스
  5. RuntimeAnalyzer → 최종 서비스 목록
  6. (선택) AI 보완 분석
  7. ScanResult 반환
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from aidevops.analyzer.runtime_analyzer import analyze as runtime_analyze
from aidevops.models.project import Dependency, ScanResult
from aidevops.scanner import config_parser, dependency_parser, file_detector, language_detector

logger = logging.getLogger("aidevops.scanner")


async def scan(
    project_path: str,
    ai_provider=None,
) -> ScanResult:
    """
    프로젝트를 분석하여 ScanResult를 반환한다.

    ai_provider: AIProvider 인스턴스 (None이면 Rule Engine만 사용)
    """
    root = Path(project_path).resolve()
    if not root.exists():
        raise ValueError(f"프로젝트 경로가 존재하지 않습니다: {project_path}")
    if not root.is_dir():
        raise ValueError(f"경로가 디렉토리가 아닙니다: {project_path}")

    logger.info("스캔 시작: %s", root)

    # 1. 파일 탐지
    files = file_detector.detect(root)
    detected_file_names = list(files.found.keys())

    # 2. 의존성 파싱
    deps: list[Dependency] = dependency_parser.parse(files, root)
    logger.debug("탐지된 의존성: %d개", len(deps))

    # 3. 언어/프레임워크 탐지
    lang_info = language_detector.detect(files, deps, root)
    logger.debug("언어: %s / 프레임워크: %s", lang_info.language, lang_info.framework)

    # 4. 설정 파일 파싱
    config_services = config_parser.parse(files, root)

    # 5. 런타임 요구사항 분석
    runtime = runtime_analyze(deps, config_services)

    # 6. 기존 Docker/CI-CD 탐지
    existing_docker = files.has("Dockerfile") or files.has("docker-compose.yml") or files.has("docker-compose.yaml")
    existing_cicd = files.existing_cicd

    # 7. AI 보완 분석 (실패해도 결과에 영향 없음)
    ai_notes: dict = {}
    if ai_provider:
        try:
            ai_notes = await _ai_enhance(ai_provider, root, lang_info, runtime, deps)
        except Exception as e:
            logger.warning("AI 분석 실패 (규칙 기반 결과 사용): %s", e)

    # 8. 신뢰도 계산
    confidence = _calc_confidence(lang_info, deps, runtime, ai_notes)

    result = ScanResult(
        project_id=str(uuid.uuid4()),
        path=str(root),
        name=root.name,
        language=lang_info.language,
        framework=lang_info.framework,
        language_version=lang_info.language_version,
        build_tool=lang_info.build_tool,
        database=runtime.database,
        message_queue=runtime.message_queue,
        cache=runtime.cache,
        storage=runtime.storage,
        external_services=runtime.external_services,
        existing_docker=existing_docker,
        existing_cicd=existing_cicd,
        dependencies=deps[:100],      # 최대 100개만 저장
        config_files=detected_file_names,
        scan_confidence=confidence,
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )
    logger.info("스캔 완료: %s (신뢰도: %.2f)", root.name, confidence)
    return result


async def _ai_enhance(ai_provider, root: Path, lang_info, runtime, deps) -> dict:
    """AI로 보완 분석을 수행하고 추가 정보를 반환한다."""
    # 코드 전체 전송 금지 - 스캔 결과 요약만 전달
    context = {
        "language": lang_info.language,
        "framework": lang_info.framework,
        "detected_services": {
            "database": runtime.database,
            "message_queue": runtime.message_queue,
            "cache": runtime.cache,
        },
        "top_deps": [d.name for d in deps[:20]],
    }

    # README가 있으면 첫 50줄만 전달
    readme = root / "README.md"
    if readme.exists():
        lines = readme.read_text(encoding="utf-8", errors="ignore").splitlines()[:50]
        context["readme_summary"] = "\n".join(lines)

    prompt = f"""다음은 프로젝트 스캔 결과입니다:
{json.dumps(context, ensure_ascii=False, indent=2)}

정적 분석으로 탐지되지 않은 추가 서비스나 요구사항이 있으면 알려주세요.
반드시 JSON 형식으로만 응답하세요:
{{"additional_database": [], "additional_services": [], "notes": "", "confidence_boost": 0.0}}
"""
    response = await ai_provider.complete(prompt)
    # JSON 파싱 시도
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response[start:end])
    return {}


def _calc_confidence(lang_info, deps, runtime, ai_notes) -> float:
    score = lang_info.confidence

    # 의존성이 많을수록 신뢰도 소폭 증가
    if len(deps) > 5:
        score = min(score + 0.02, 1.0)
    if lang_info.framework:
        score = min(score + 0.03, 1.0)
    if ai_notes.get("confidence_boost"):
        score = min(score + float(ai_notes["confidence_boost"]), 1.0)

    return round(score, 2)
