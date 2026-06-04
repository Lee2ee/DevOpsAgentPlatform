"""
application.yml, application.properties, .env, docker-compose.yml 등을 파싱하여
설정 기반 외부 서비스 정보를 추출한다.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from aidevops.scanner.file_detector import DetectedFiles


@dataclass
class ConfigServices:
    database: list[str] = field(default_factory=list)
    message_queue: list[str] = field(default_factory=list)
    cache: list[str] = field(default_factory=list)
    storage: list[str] = field(default_factory=list)
    external_services: list[str] = field(default_factory=list)


def parse(files: DetectedFiles, root: Path) -> ConfigServices:
    result = ConfigServices()

    # application.yml / yaml
    for key in ("application.yml", "application.yaml"):
        if files.has(key):
            _parse_spring_yaml(files.path_of(key), result)

    # application.properties
    if files.has("application.properties"):
        _parse_spring_properties(files.path_of("application.properties"), result)

    # .env
    if files.has(".env"):
        _parse_dotenv(files.path_of(".env"), result)
    if files.has(".env.example"):
        _parse_dotenv(files.path_of(".env.example"), result)

    # docker-compose.yml
    for key in ("docker-compose.yml", "docker-compose.yaml"):
        if files.has(key):
            _parse_compose(files.path_of(key), result)

    _dedup(result)
    return result


def _dedup(s: ConfigServices):
    s.database = _unique(s.database)
    s.message_queue = _unique(s.message_queue)
    s.cache = _unique(s.cache)
    s.storage = _unique(s.storage)
    s.external_services = _unique(s.external_services)


def _unique(lst: list[str]) -> list[str]:
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


# ── Spring YAML ────────────────────────────────────────────────

def _parse_spring_yaml(path: Path, result: ConfigServices):
    try:
        import yaml  # pyyaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        spring = data.get("spring", {})

        # Datasource
        ds_url = (spring.get("datasource", {}) or {}).get("url", "")
        if ds_url:
            _classify_jdbc_url(ds_url, result)

        # Redis
        redis = spring.get("redis", {}) or spring.get("data", {}).get("redis", {})
        if redis:
            result.cache.append("redis")

        # Kafka
        kafka = spring.get("kafka", {})
        if kafka:
            result.message_queue.append("kafka")

        # RabbitMQ
        rabbitmq = spring.get("rabbitmq", {})
        if rabbitmq:
            result.message_queue.append("rabbitmq")

        # MongoDB
        mongo = spring.get("data", {}).get("mongodb", {})
        if mongo:
            result.database.append("mongodb")

        # Elasticsearch
        es = spring.get("elasticsearch", {}) or spring.get("data", {}).get("elasticsearch", {})
        if es:
            result.external_services.append("elasticsearch")

    except Exception:
        pass


# ── Spring Properties ──────────────────────────────────────────

def _parse_spring_properties(path: Path, result: ConfigServices):
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().lower()
            value = value.strip()

            if "datasource.url" in key:
                _classify_jdbc_url(value, result)
            elif "spring.redis" in key or "spring.data.redis" in key:
                result.cache.append("redis")
            elif "spring.kafka" in key:
                result.message_queue.append("kafka")
            elif "spring.rabbitmq" in key:
                result.message_queue.append("rabbitmq")
            elif "spring.data.mongodb" in key:
                result.database.append("mongodb")
            elif "spring.elasticsearch" in key:
                result.external_services.append("elasticsearch")
    except Exception:
        pass


# ── .env ───────────────────────────────────────────────────────

_ENV_DB_PATTERNS = [
    (r"jdbc:oracle", "oracle"),
    (r"jdbc:mysql|mysql://", "mysql"),
    (r"jdbc:postgresql|postgresql://|postgres://", "postgresql"),
    (r"mongodb://|mongodb\+srv://", "mongodb"),
    (r"redis://", "redis"),
    (r"kafka://|KAFKA_BROKERS", "kafka"),
    (r"amqp://|rabbitmq", "rabbitmq"),
    (r"s3://|AWS_S3|S3_BUCKET", "s3"),
    (r"minio", "minio"),
    (r"elasticsearch", "elasticsearch"),
]


def _parse_dotenv(path: Path, result: ConfigServices):
    try:
        text = path.read_text(encoding="utf-8").upper()
        for pattern, service in _ENV_DB_PATTERNS:
            if re.search(pattern.upper(), text):
                _add_service(service, result)
    except Exception:
        pass


# ── docker-compose.yml ─────────────────────────────────────────

_COMPOSE_SERVICE_MAP = {
    "mysql": ("mysql", "database"),
    "mariadb": ("mariadb", "database"),
    "postgres": ("postgresql", "database"),
    "oracle": ("oracle", "database"),
    "mongodb": ("mongodb", "database"),
    "mongo": ("mongodb", "database"),
    "redis": ("redis", "cache"),
    "kafka": ("kafka", "message_queue"),
    "zookeeper": (None, None),
    "rabbitmq": ("rabbitmq", "message_queue"),
    "elasticsearch": ("elasticsearch", "external_services"),
    "kibana": (None, None),
    "minio": ("minio", "storage"),
    "nginx": (None, None),
}


def _parse_compose(path: Path, result: ConfigServices):
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        services = data.get("services", {})
        for svc_name, svc_config in services.items():
            # 이미지명으로 서비스 탐지
            image = (svc_config or {}).get("image", "").lower().split(":")[0].split("/")[-1]
            for keyword, (name, category) in _COMPOSE_SERVICE_MAP.items():
                if keyword in image or keyword in svc_name.lower():
                    if name and category:
                        getattr(result, category).append(name)
                    break
    except Exception:
        pass


# ── helpers ────────────────────────────────────────────────────

def _classify_jdbc_url(url: str, result: ConfigServices):
    url_lower = url.lower()
    if "oracle" in url_lower:
        result.database.append("oracle")
    elif "mysql" in url_lower:
        result.database.append("mysql")
    elif "postgresql" in url_lower or "postgres" in url_lower:
        result.database.append("postgresql")
    elif "mariadb" in url_lower:
        result.database.append("mariadb")
    elif "sqlserver" in url_lower or "mssql" in url_lower:
        result.database.append("mssql")
    elif "h2" in url_lower:
        result.database.append("h2")


def _add_service(service: str, result: ConfigServices):
    db_services = {"oracle", "mysql", "postgresql", "mariadb", "mongodb", "mssql", "h2"}
    cache_services = {"redis", "memcached"}
    mq_services = {"kafka", "rabbitmq"}
    storage_services = {"s3", "minio"}
    if service in db_services:
        result.database.append(service)
    elif service in cache_services:
        result.cache.append(service)
    elif service in mq_services:
        result.message_queue.append(service)
    elif service in storage_services:
        result.storage.append(service)
    else:
        result.external_services.append(service)
