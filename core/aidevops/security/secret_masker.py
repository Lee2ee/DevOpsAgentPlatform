"""
로그, 응답, AI 전달 데이터에서 민감 정보를 마스킹한다.
"""

import re

# (패턴, 대체 문자열) 순서대로 적용
_RULES: list[tuple[re.Pattern, str]] = [
    # SSH Private Key 블록
    (
        re.compile(r"-----BEGIN[A-Z ]+PRIVATE KEY-----.*?-----END[A-Z ]+PRIVATE KEY-----", re.DOTALL),
        "[SSH_KEY_MASKED]",
    ),
    # URL 안의 비밀번호: scheme://user:PASSWORD@host
    (
        re.compile(r"(://[^:/@\s]+:)[^@\s]{1,}(@)"),
        r"\1[MASKED]\2",
    ),
    # JDBC URL: :user:PASSWORD@host 또는 :user/PASSWORD@host
    (
        re.compile(r"(:[^:/@\s]{1,64}[:/])[^@\s]{4,}(@)"),
        r"\1[MASKED]\2",
    ),
    # Bearer / Basic 토큰
    (
        re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/=]{10,}", re.IGNORECASE),
        r"\1[TOKEN_MASKED]",
    ),
    # Authorization 헤더 값
    (
        re.compile(r"(Authorization['\"]?\s*[:=]\s*['\"]?)[^\s'\"]{10,}", re.IGNORECASE),
        r"\1[MASKED]",
    ),
    # sk- 형식 API Key (OpenAI, Anthropic 등)
    (
        re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
        "[API_KEY_MASKED]",
    ),
    # api_key / api-key 값
    (
        re.compile(r"(api[-_]?key['\"\s:=]+)['\"]?[\w\-]{16,}['\"]?", re.IGNORECASE),
        r"\1[MASKED]",
    ),
    # password 키-값 (JSON, YAML, env 형식 모두)
    (
        re.compile(r"(password['\"\s:=]+)['\"]?[^\s'\"\n]{4,}['\"]?", re.IGNORECASE),
        r"\1[MASKED]",
    ),
    # secret 키-값
    (
        re.compile(r"(secret['\"\s:=]+)['\"]?[^\s'\"\n]{8,}['\"]?", re.IGNORECASE),
        r"\1[MASKED]",
    ),
    # AWS 자격증명
    (
        re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
        "[AWS_ACCESS_KEY_MASKED]",
    ),
]


def mask(text: str) -> str:
    """텍스트에서 민감 정보를 마스킹하여 반환한다."""
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text


def mask_dict(data: dict) -> dict:
    """dict의 값을 재귀적으로 마스킹한다 (로그/응답 정제용)."""
    _SENSITIVE_KEYS = frozenset({
        "password", "passwd", "secret", "api_key", "apikey",
        "private_key", "ssh_key", "token", "credential",
        "encrypted_value", "value",
    })
    result = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_KEYS:
            result[k] = "[MASKED]"
        elif isinstance(v, dict):
            result[k] = mask_dict(v)
        elif isinstance(v, str):
            result[k] = mask(v)
        else:
            result[k] = v
    return result
