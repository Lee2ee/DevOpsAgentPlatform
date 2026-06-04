from fastapi import APIRouter

from aidevops.api.routers.health import router as health_router
from aidevops.api.routers.config_router import router as config_router
from aidevops.api.routers.projects import router as projects_router
from aidevops.api.routers.docker import router as docker_router
from aidevops.api.routers.cicd import router as cicd_router
from aidevops.api.routers.audit import router as audit_router
from aidevops.api.routers.deploy import router as deploy_router
from aidevops.api.routers.ws import router as ws_router
from aidevops.api.routers.analyze import router as analyze_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(config_router)
api_router.include_router(projects_router)
api_router.include_router(docker_router)
api_router.include_router(cicd_router)
api_router.include_router(audit_router)
api_router.include_router(deploy_router)
api_router.include_router(ws_router)
api_router.include_router(analyze_router)
