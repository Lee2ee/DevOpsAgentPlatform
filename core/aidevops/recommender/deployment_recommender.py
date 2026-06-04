"""
프로젝트 스캔 결과를 분석하여 배포 환경 + CI/CD 조합을 추천한다.
"""
from aidevops.models.project import ScanResult, Recommendation, DeployCombo


def _combos_small(existing_cicd: str) -> list[DeployCombo]:
    combos = [
        DeployCombo(
            id="docker_vps_gha",
            deploy_name="Docker + 단독 VPS",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="docker",
            description="단일 컨테이너를 VPS에 배포하고, GitHub Actions가 코드 푸시 시 자동으로 빌드·SSH 배포.",
            synergy="GitHub Actions의 SSH 액션으로 VPS에 직접 배포 가능. 추가 인프라 없이 완전 자동화.",
            pros=["가장 낮은 비용 (VPS $5~15/월)", "설정 간단·빠른 시작", "GitHub 코드 푸시 → 자동 배포"],
            cons=["수동 스케일링", "고가용성 없음"],
            estimated_cost="월 $5~15 (VPS) + GitHub Actions 무료 플랜",
            complexity="simple",
            score=5,
            recommended=True,
        ),
        DeployCombo(
            id="oracle_free_gha",
            deploy_name="Oracle Cloud Free Tier VM",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="oracle",
            description="Oracle Cloud Always Free VM에 Docker 배포. GitHub Actions가 SSH로 자동 배포.",
            synergy="인프라 비용 0원, CI/CD도 GitHub Actions 무료 플랜 사용. 완전 무료 자동화 스택.",
            pros=["인프라 완전 무료 (Always Free)", "4코어 24GB ARM VM", "CI/CD 무료"],
            cons=["Oracle 계정 필요", "ARM 아키텍처 호환성 확인 필요"],
            estimated_cost="무료",
            complexity="simple",
            score=4,
        ),
        DeployCombo(
            id="railway_gha",
            deploy_name="Railway / Fly.io (PaaS)",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="railway",
            description="Railway나 Fly.io에 배포. GitHub Actions 없이도 Git 푸시만으로 자동 배포 가능.",
            synergy="PaaS 자체 CI/CD + GitHub Actions 선택적 사용. 인프라 관리 완전 불필요.",
            pros=["Git push → 자동 배포", "인프라 관리 불필요", "HTTPS 자동 설정"],
            cons=["무료 플랜 제한", "커스터마이징 한계"],
            estimated_cost="월 $0~20 (사용량 기반)",
            complexity="simple",
            score=3,
        ),
    ]
    return _apply_existing_cicd(combos, existing_cicd)


def _combos_medium(infra_services: list[str], existing_cicd: str) -> list[DeployCombo]:
    svc_str = ", ".join(infra_services[:3]) if infra_services else "DB/캐시"
    combos = [
        DeployCombo(
            id="compose_vps_gha",
            deploy_name="Docker Compose + VPS",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="docker",
            description=f"Docker Compose로 앱과 인프라({svc_str})를 한 서버에서 운영. GitHub Actions가 자동 배포.",
            synergy="Compose 파일 하나로 앱+인프라 통합 관리. GitHub Actions SSH 배포로 `docker compose up -d` 자동 실행.",
            pros=["인프라 포함 원클릭 배포", "저렴한 비용", "환경 재현성 보장"],
            cons=["단일 서버 의존", "수동 스케일링"],
            estimated_cost="월 $20~60 (VPS)",
            complexity="simple",
            score=5,
            recommended=True,
        ),
        DeployCombo(
            id="aws_ec2_gha",
            deploy_name="AWS EC2 + Docker Compose",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="aws",
            description="AWS EC2에 Docker Compose 배포. GitHub Actions가 ECR 이미지 푸시 후 EC2에 SSH 배포.",
            synergy="GitHub Actions → ECR 빌드/푸시 → EC2 SSH 배포. AWS 생태계(RDS, ElastiCache) 연동 용이.",
            pros=["AWS 생태계 연동", "RDS·ElastiCache 대체 가능", "CloudWatch 모니터링"],
            cons=["비용 높음 ($50~150/월)", "AWS 지식 필요"],
            estimated_cost="월 $50~150",
            complexity="moderate",
            score=4,
        ),
        DeployCombo(
            id="oracle_oci_gitlab",
            deploy_name="Oracle Cloud (OCI) VM",
            cicd_name="GitLab CI",
            cicd_id="gitlab_ci",
            platform="oracle",
            description="OCI VM에 Docker Compose 배포. GitLab CI Runner를 OCI에 직접 설치해 비용 최적화.",
            synergy="OCI의 저렴한 VM에 GitLab Runner 설치 → CI/CD 비용까지 절감. AWS 대비 30~50% 저렴.",
            pros=["AWS보다 30~50% 저렴", "GitLab 셀프 호스팅 연동", "$300 무료 크레딧"],
            cons=["한국 리전 없음", "AWS보다 생태계 작음"],
            estimated_cost="월 $20~80",
            complexity="moderate",
            score=3,
        ),
    ]
    return _apply_existing_cicd(combos, existing_cicd)


def _combos_large(existing_cicd: str) -> list[DeployCombo]:
    combos = [
        DeployCombo(
            id="aws_ecs_gha",
            deploy_name="AWS ECS / Fargate",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="aws",
            description="AWS 관리형 컨테이너 서비스. GitHub Actions가 ECR 빌드 후 ECS 서비스 자동 업데이트.",
            synergy="GitHub Actions → ECR 빌드 → ECS 롤링 업데이트. 서버 관리 없이 컨테이너 오케스트레이션 자동화.",
            pros=["서버 관리 불필요", "자동 스케일링", "RDS·ElastiCache 통합", "무중단 롤링 배포"],
            cons=["비용 높음 ($150~500/월)", "ECS 학습 필요"],
            estimated_cost="월 $150~500+",
            complexity="moderate",
            score=5,
            recommended=True,
        ),
        DeployCombo(
            id="aws_eks_gha",
            deploy_name="AWS EKS (Kubernetes)",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="aws",
            description="AWS 관리형 Kubernetes. GitHub Actions가 Helm Chart 배포 또는 kubectl apply 자동화.",
            synergy="GitHub Actions → Docker 빌드 → ECR 푸시 → kubectl/Helm으로 EKS 배포. 업계 표준 GitOps 파이프라인.",
            pros=["업계 표준 Kubernetes", "무한 스케일링", "강력한 생태계", "멀티 팀 지원"],
            cons=["높은 학습 곡선", "비용 높음 (클러스터 $0.10/h+)"],
            estimated_cost="월 $200~1000+",
            complexity="complex",
            score=4,
        ),
        DeployCombo(
            id="oracle_oke_gitlab",
            deploy_name="Oracle OKE (Kubernetes)",
            cicd_name="GitLab CI",
            cicd_id="gitlab_ci",
            platform="oracle",
            description="Oracle 관리형 Kubernetes. GitLab CI가 OCI Container Registry 빌드 후 OKE 배포.",
            synergy="GitLab CI + OCI Registry + OKE 네이티브 통합. EKS 대비 Control Plane 무료, 노드 비용 저렴.",
            pros=["EKS보다 30~40% 저렴", "Control Plane 무료", "GitLab 셀프 호스팅 연동"],
            cons=["AWS보다 생태계 작음", "한국 리전 없음"],
            estimated_cost="월 $100~500",
            complexity="complex",
            score=3,
        ),
    ]
    return _apply_existing_cicd(combos, existing_cicd)


def _combos_enterprise(existing_cicd: str) -> list[DeployCombo]:
    combos = [
        DeployCombo(
            id="aws_eks_multi_gha",
            deploy_name="AWS EKS + 멀티 AZ",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="aws",
            description="다중 가용 영역 EKS + ArgoCD GitOps. GitHub Actions가 이미지 빌드, ArgoCD가 배포 관리.",
            synergy="GitHub Actions → ECR 빌드 → ArgoCD 자동 동기화 → EKS 무중단 배포. 엔터프라이즈 GitOps 표준.",
            pros=["99.99% SLA", "GitOps 자동화 (ArgoCD)", "멀티 리전 확장 가능", "엔터프라이즈 지원"],
            cons=["높은 비용 ($1000+/월)", "전문 DevOps 엔지니어 필요"],
            estimated_cost="월 $1000+",
            complexity="complex",
            score=5,
            recommended=True,
        ),
        DeployCombo(
            id="gcp_gke_cloudbuild",
            deploy_name="GCP GKE (Kubernetes)",
            cicd_name="GitHub Actions",
            cicd_id="github_actions",
            platform="gcp",
            description="Google Cloud GKE Autopilot + GitHub Actions. 노드 관리 자동화, AI/ML 워크로드 친화적.",
            synergy="GitHub Actions → Artifact Registry 빌드 → GKE Autopilot 배포. 노드 프로비저닝 자동으로 운영 부담 최소화.",
            pros=["Autopilot 모드 (노드 자동 관리)", "BigQuery·Vertex AI 통합", "Google 글로벌 네트워크"],
            cons=["비용 높음", "GCP 지식 필요"],
            estimated_cost="월 $800+",
            complexity="complex",
            score=4,
        ),
        DeployCombo(
            id="azure_aks_devops",
            deploy_name="Azure AKS",
            cicd_name="Azure DevOps",
            cicd_id="azure_devops",
            platform="azure",
            description="Azure AKS + Azure DevOps 파이프라인. Microsoft 생태계 완전 통합, Active Directory 보안.",
            synergy="Azure DevOps → ACR 빌드 → AKS 배포. Azure AD, Key Vault, Monitor 네이티브 통합으로 기업 보안 충족.",
            pros=["Microsoft 생태계 완전 통합", "Azure AD·Key Vault 연동", "엔터프라이즈 보안·감사"],
            cons=["비용 높음", "Azure 종속"],
            estimated_cost="월 $800+",
            complexity="complex",
            score=3,
        ),
    ]
    return _apply_existing_cicd(combos, existing_cicd)


def _apply_existing_cicd(combos: list[DeployCombo], existing_cicd: str) -> list[DeployCombo]:
    """기존 CI/CD가 있으면 해당 CI/CD를 쓰는 콤보를 최우선으로 올린다."""
    if not existing_cicd or existing_cicd in ("none", ""):
        return combos

    matched = [c for c in combos if c.cicd_id == existing_cicd]
    others = [c for c in combos if c.cicd_id != existing_cicd]

    if matched:
        matched[0] = matched[0].model_copy(update={"recommended": True, "score": 5})
        return (matched + others)[:3]
    return combos


def recommend(scan: ScanResult) -> Recommendation:
    """ScanResult를 분석하여 배포 환경 + CI/CD 조합 추천을 반환한다."""
    infra_services = (
        scan.database + scan.message_queue + scan.cache + scan.external_services
    )
    infra_count = len(infra_services)
    dep_count = len(scan.dependencies)
    existing_cicd = scan.existing_cicd if scan.existing_cicd not in ("none", "") else ""

    if infra_count == 0 and dep_count < 15:
        scale, scale_label = "small", "소규모"
        scale_reason = f"단일 서비스 · 외부 인프라 없음 · 의존성 {dep_count}개"
        combos = _combos_small(existing_cicd)
    elif infra_count <= 2 and dep_count < 40:
        scale, scale_label = "medium", "중규모"
        scale_reason = f"인프라 서비스 {infra_count}개 · 의존성 {dep_count}개"
        combos = _combos_medium(infra_services, existing_cicd)
    elif infra_count <= 5:
        scale, scale_label = "large", "대규모"
        scale_reason = f"인프라 서비스 {infra_count}개 · 의존성 {dep_count}개"
        combos = _combos_large(existing_cicd)
    else:
        scale, scale_label = "enterprise", "엔터프라이즈"
        scale_reason = f"복잡한 인프라 {infra_count}개 서비스 · 의존성 {dep_count}개"
        combos = _combos_enterprise(existing_cicd)

    return Recommendation(
        project_id=scan.project_id,
        scale=scale,
        scale_label=scale_label,
        scale_reason=scale_reason,
        infra_count=infra_count,
        dep_count=dep_count,
        infra_services=infra_services,
        combos=combos,
    )
