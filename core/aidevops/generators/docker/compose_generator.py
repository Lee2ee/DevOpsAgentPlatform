"""
ScanResult를 기반으로 docker-compose.yml을 생성한다.
앱 서비스 + 탐지된 의존 서비스(Redis, Kafka, PostgreSQL 등)를 포함한다.
"""

from aidevops.models.project import ScanResult

# Oracle은 라이선스 이슈로 공식 이미지 제공 불가
_NO_COMPOSE_DBS = {"oracle", "mssql"}

_SERVICE_DEFINITIONS: dict[str, dict] = {
    "mysql": {
        "image": "mysql:8.0",
        "environment": {
            "MYSQL_ROOT_PASSWORD": "root",
            "MYSQL_DATABASE": "${DB_NAME:-appdb}",
            "MYSQL_USER": "${DB_USER:-app}",
            "MYSQL_PASSWORD": "${DB_PASSWORD:-secret}",
        },
        "volumes": ["mysql_data:/var/lib/mysql"],
        "healthcheck": {
            "test": ["CMD", "mysqladmin", "ping", "-h", "localhost"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
        },
    },
    "mariadb": {
        "image": "mariadb:11",
        "environment": {
            "MARIADB_ROOT_PASSWORD": "root",
            "MARIADB_DATABASE": "${DB_NAME:-appdb}",
            "MARIADB_USER": "${DB_USER:-app}",
            "MARIADB_PASSWORD": "${DB_PASSWORD:-secret}",
        },
        "volumes": ["mariadb_data:/var/lib/mysql"],
    },
    "postgresql": {
        "image": "postgres:16-alpine",
        "environment": {
            "POSTGRES_DB": "${DB_NAME:-appdb}",
            "POSTGRES_USER": "${DB_USER:-app}",
            "POSTGRES_PASSWORD": "${DB_PASSWORD:-secret}",
        },
        "volumes": ["postgres_data:/var/lib/postgresql/data"],
        "healthcheck": {
            "test": ["CMD-SHELL", "pg_isready -U ${DB_USER:-app}"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
        },
    },
    "mongodb": {
        "image": "mongo:7",
        "environment": {
            "MONGO_INITDB_ROOT_USERNAME": "${MONGO_USER:-admin}",
            "MONGO_INITDB_ROOT_PASSWORD": "${MONGO_PASSWORD:-secret}",
            "MONGO_INITDB_DATABASE": "${DB_NAME:-appdb}",
        },
        "volumes": ["mongo_data:/data/db"],
    },
    "redis": {
        "image": "redis:7-alpine",
        "volumes": ["redis_data:/data"],
        "healthcheck": {
            "test": ["CMD", "redis-cli", "ping"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
        },
    },
    "kafka": {
        "image": "apache/kafka:latest",
        "environment": {
            "KAFKA_NODE_ID": "1",
            "KAFKA_PROCESS_ROLES": "broker,controller",
            "KAFKA_LISTENERS": "PLAINTEXT://:9092,CONTROLLER://:9093",
            "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://kafka:9092",
            "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP": "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
            "KAFKA_CONTROLLER_QUORUM_VOTERS": "1@kafka:9093",
            "KAFKA_CONTROLLER_LISTENER_NAMES": "CONTROLLER",
            "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": "1",
            "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR": "1",
            "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR": "1",
            "CLUSTER_ID": "MkU3OEVBNTcwNTJENDM2Qk",
        },
        "volumes": ["kafka_data:/var/lib/kafka/data"],
        "healthcheck": {
            "test": ["CMD-SHELL", "/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s",
        },
    },
    "rabbitmq": {
        "image": "rabbitmq:3.13-management-alpine",
        "ports": ["5672:5672", "15672:15672"],
        "environment": {
            "RABBITMQ_DEFAULT_USER": "${RABBITMQ_USER:-admin}",
            "RABBITMQ_DEFAULT_PASS": "${RABBITMQ_PASSWORD:-secret}",
        },
        "volumes": ["rabbitmq_data:/var/lib/rabbitmq"],
        "healthcheck": {
            "test": ["CMD", "rabbitmq-diagnostics", "ping"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        },
    },
    "elasticsearch": {
        "image": "elasticsearch:8.13.0",
        "environment": {
            "discovery.type": "single-node",
            "ES_JAVA_OPTS": "-Xms512m -Xmx512m",
            "xpack.security.enabled": "false",
        },
        "volumes": ["es_data:/usr/share/elasticsearch/data"],
    },
    "minio": {
        "image": "minio/minio:latest",
        "command": "server /data --console-address :9001",
        "ports": ["9000:9000", "9001:9001"],
        "environment": {
            "MINIO_ROOT_USER": "${MINIO_USER:-minioadmin}",
            "MINIO_ROOT_PASSWORD": "${MINIO_PASSWORD:-minioadmin}",
        },
        "volumes": ["minio_data:/data"],
    },
}

# 서비스별 볼륨명
_VOLUME_NAMES: dict[str, str] = {
    "mysql": "mysql_data",
    "mariadb": "mariadb_data",
    "postgresql": "postgres_data",
    "mongodb": "mongo_data",
    "redis": "redis_data",
    "kafka": "kafka_data",
    "rabbitmq": "rabbitmq_data",
    "elasticsearch": "es_data",
    "minio": "minio_data",
}

_FRAMEWORK_PORTS: dict[str, int] = {
    "springboot": 8080, "quarkus": 8080, "micronaut": 8080,
    "express": 3000, "fastify": 3000, "nestjs": 3000, "nextjs": 3000,
    "fastapi": 8000, "django": 8000, "flask": 5000,
    "gin": 8080, "echo": 8080,
}


def generate_compose(scan: ScanResult, registry: str | None = None) -> tuple[str, list[str]]:
    """
    docker-compose.yml 내용과 경고 목록을 반환한다.
    """
    import yaml

    warnings: list[str] = []
    all_services: list[str] = (
        scan.database + scan.cache + scan.message_queue +
        scan.storage + scan.external_services
    )
    # 중복 제거
    seen: set[str] = set()
    unique_services = [s for s in all_services if not (s in seen or seen.add(s))]

    port = _FRAMEWORK_PORTS.get((scan.framework or "").lower(), 8080)
    image_name = f"{scan.name}:latest"
    if registry:
        image_name = f"{registry}/{scan.name}:latest"

    compose: dict = {
        "services": {},
        "volumes": {},
        "networks": {
            "app-network": {"driver": "bridge"},
        },
    }

    dep_service_names: list[str] = []

    # 의존 서비스 추가
    for svc in unique_services:
        if svc in _NO_COMPOSE_DBS:
            if svc == "oracle":
                warnings.append(
                    "Oracle DB는 라이선스 계약으로 공식 Docker 이미지를 제공하지 않아 compose에 포함할 수 없습니다. "
                    "대신 앱 서비스에 SPRING_DATASOURCE_URL 환경변수가 추가됩니다. "
                    "Oracle DB 서버 주소를 해당 환경변수에 직접 입력하세요."
                )
            else:
                warnings.append(
                    f"'{svc}'는 라이선스 제약으로 공식 Docker 이미지를 compose에 포함할 수 없습니다. "
                    f"외부 {svc.upper()} 서버 URL을 환경변수로 설정하세요."
                )
            continue

        if svc in _SERVICE_DEFINITIONS:
            svc_def = dict(_SERVICE_DEFINITIONS[svc])
            svc_def["networks"] = ["app-network"]
            compose["services"][svc] = svc_def
            dep_service_names.append(svc)

            if svc in _VOLUME_NAMES:
                compose["volumes"][_VOLUME_NAMES[svc]] = None

    # 앱 서비스
    app_service: dict = {
        "build": {"context": ".", "dockerfile": "Dockerfile"},
        "ports": [f"{port}:{port}"],
        "networks": ["app-network"],
        "restart": "unless-stopped",
        "environment": _build_app_env(scan),
    }
    if dep_service_names:
        app_service["depends_on"] = {
            svc: {"condition": "service_healthy"}
            if "healthcheck" in compose["services"].get(svc, {})
            else {"condition": "service_started"}
            for svc in dep_service_names
        }

    # registry가 있으면 image도 명시
    if registry:
        app_service["image"] = image_name

    compose["services"][scan.name] = app_service

    # 볼륨이 없으면 키 제거
    if not compose["volumes"]:
        del compose["volumes"]

    content = "# Auto-generated by AI DevOps Agent\n"
    content += yaml.dump(compose, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return content, warnings


def _build_app_env(scan: ScanResult) -> dict[str, str]:
    """앱 서비스의 환경변수 템플릿을 생성한다."""
    lang = (scan.language or "").lower()
    fw = (scan.framework or "").lower()
    is_spring = lang in ("java", "kotlin") and "spring" in fw
    env: dict[str, str] = {}

    for db in scan.database:
        if db == "mysql":
            if is_spring:
                env["SPRING_DATASOURCE_URL"] = "jdbc:mysql://mysql:3306/${DB_NAME:-appdb}"
                env["SPRING_DATASOURCE_USERNAME"] = "${DB_USER:-app}"
                env["SPRING_DATASOURCE_PASSWORD"] = "${DB_PASSWORD:-secret}"
            else:
                env["DATABASE_URL"] = "mysql://${DB_USER:-app}:${DB_PASSWORD:-secret}@mysql:3306/${DB_NAME:-appdb}"
        elif db == "postgresql":
            if is_spring:
                env["SPRING_DATASOURCE_URL"] = "jdbc:postgresql://postgresql:5432/${DB_NAME:-appdb}"
                env["SPRING_DATASOURCE_USERNAME"] = "${DB_USER:-app}"
                env["SPRING_DATASOURCE_PASSWORD"] = "${DB_PASSWORD:-secret}"
            else:
                env["DATABASE_URL"] = "postgresql://${DB_USER:-app}:${DB_PASSWORD:-secret}@postgresql:5432/${DB_NAME:-appdb}"
        elif db == "mongodb":
            if is_spring:
                env["SPRING_DATA_MONGODB_URI"] = "mongodb://${MONGO_USER:-admin}:${MONGO_PASSWORD:-secret}@mongodb:27017/${DB_NAME:-appdb}"
            else:
                env["MONGODB_URI"] = "mongodb://${MONGO_USER:-admin}:${MONGO_PASSWORD:-secret}@mongodb:27017/${DB_NAME:-appdb}"
        elif db == "oracle":
            env["SPRING_DATASOURCE_URL"] = "jdbc:oracle:thin:@${ORACLE_HOST:-localhost}:${ORACLE_PORT:-1521}/${ORACLE_SERVICE:-ORCLPDB1}"
            env["SPRING_DATASOURCE_USERNAME"] = "${DB_USER:-app}"
            env["SPRING_DATASOURCE_PASSWORD"] = "${DB_PASSWORD:-secret}"
            env["SPRING_DATASOURCE_DRIVER_CLASS_NAME"] = "oracle.jdbc.OracleDriver"

    for cache in scan.cache:
        if cache == "redis":
            if is_spring:
                env["SPRING_REDIS_HOST"] = "redis"
                env["SPRING_REDIS_PORT"] = "6379"
            else:
                env["REDIS_URL"] = "redis://redis:6379"

    for mq in scan.message_queue:
        if mq == "kafka":
            if is_spring:
                env["SPRING_KAFKA_BOOTSTRAP_SERVERS"] = "kafka:9092"
            else:
                env["KAFKA_BROKERS"] = "kafka:9092"
        elif mq == "rabbitmq":
            if is_spring:
                env["SPRING_RABBITMQ_HOST"] = "rabbitmq"
            else:
                env["RABBITMQ_URL"] = "amqp://${RABBITMQ_USER:-admin}:${RABBITMQ_PASSWORD:-secret}@rabbitmq:5672"

    return env
