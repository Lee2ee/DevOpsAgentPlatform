"""
Rule Engine 기반 Runtime Analyzer.
의존성 목록과 설정 파싱 결과를 종합하여 필요한 외부 서비스를 최종 결정한다.
"""

from dataclasses import dataclass, field

from aidevops.models.project import Dependency
from aidevops.scanner.config_parser import ConfigServices


@dataclass
class RuntimeRequirements:
    database: list[str] = field(default_factory=list)
    message_queue: list[str] = field(default_factory=list)
    cache: list[str] = field(default_factory=list)
    storage: list[str] = field(default_factory=list)
    external_services: list[str] = field(default_factory=list)


# 의존성명 → (서비스명, 카테고리)
_DEP_RULES: list[tuple[str, str, str]] = [
    # DB
    ("ojdbc", "oracle", "database"),
    ("oracle", "oracle", "database"),
    ("mysql-connector", "mysql", "database"),
    ("mariadb", "mariadb", "database"),
    ("postgresql", "postgresql", "database"),
    ("pg", "postgresql", "database"),
    ("spring-data-jpa", "rdbms", "database"),      # 정확한 DB는 config에서
    ("hibernate", "rdbms", "database"),
    ("sqlalchemy", "rdbms", "database"),
    ("django.db", "rdbms", "database"),
    ("pymysql", "mysql", "database"),
    ("psycopg", "postgresql", "database"),
    ("psycopg2", "postgresql", "database"),
    ("motor", "mongodb", "database"),
    ("pymongo", "mongodb", "database"),
    ("spring-data-mongodb", "mongodb", "database"),
    ("mongoengine", "mongodb", "database"),
    # Cache / Redis
    ("spring-data-redis", "redis", "cache"),
    ("jedis", "redis", "cache"),
    ("lettuce", "redis", "cache"),
    ("redis", "redis", "cache"),
    ("ioredis", "redis", "cache"),
    ("aioredis", "redis", "cache"),
    ("memcached", "memcached", "cache"),
    # Message Queue
    ("spring-kafka", "kafka", "message_queue"),
    ("kafka", "kafka", "message_queue"),
    ("spring-amqp", "rabbitmq", "message_queue"),
    ("spring-rabbit", "rabbitmq", "message_queue"),
    ("amqplib", "rabbitmq", "message_queue"),
    ("pika", "rabbitmq", "message_queue"),
    ("aiokafka", "kafka", "message_queue"),
    ("confluent-kafka", "kafka", "message_queue"),
    ("aio-pika", "rabbitmq", "message_queue"),
    # Storage
    ("aws-java-sdk-s3", "s3", "storage"),
    ("s3", "s3", "storage"),
    ("minio", "minio", "storage"),
    ("boto3", "s3", "storage"),
    ("aiobotocore", "s3", "storage"),
    # Search / Other
    ("spring-data-elasticsearch", "elasticsearch", "external_services"),
    ("elasticsearch", "elasticsearch", "external_services"),
    ("@elastic/elasticsearch", "elasticsearch", "external_services"),
]


def analyze(deps: list[Dependency], config: ConfigServices) -> RuntimeRequirements:
    """의존성 + 설정 정보를 종합하여 런타임 요구사항을 결정한다."""
    req = RuntimeRequirements()
    dep_names_lower = {d.name.lower() for d in deps}

    # 1) 의존성 기반 Rule 적용
    for dep_keyword, service, category in _DEP_RULES:
        if any(dep_keyword in d for d in dep_names_lower):
            getattr(req, category).append(service)

    # 2) 설정 파일 기반 서비스 병합
    for service in config.database:
        req.database.append(service)
    for service in config.message_queue:
        req.message_queue.append(service)
    for service in config.cache:
        req.cache.append(service)
    for service in config.storage:
        req.storage.append(service)
    for service in config.external_services:
        req.external_services.append(service)

    # 3) rdbms placeholder → 설정 기반으로 대체
    #    ("rdbms"가 있고 설정에서 구체적인 DB가 검출된 경우 제거)
    if "rdbms" in req.database and len(req.database) > 1:
        req.database = [d for d in req.database if d != "rdbms"]

    # 4) Redis가 cache와 database 양쪽에 있으면 cache로 통일
    if "redis" in req.cache and "redis" in req.database:
        req.database = [d for d in req.database if d != "redis"]

    # 5) 중복 제거
    req.database = _unique(req.database)
    req.message_queue = _unique(req.message_queue)
    req.cache = _unique(req.cache)
    req.storage = _unique(req.storage)
    req.external_services = _unique(req.external_services)

    return req


def _unique(lst: list[str]) -> list[str]:
    seen: set[str] = set()
    return [x for x in lst if not (x in seen or seen.add(x))]
