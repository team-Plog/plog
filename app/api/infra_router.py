from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode, SuccessCode
from app.common.response.response_template import ResponseTemplate
from app.models import get_db, get_async_db
from app.schemas.infra import ConnectOpenAPIInfraRequest
from app.services.infra.infra_service import build_response_get_pods_info_list, \
    update_connection_openapi_spec_and_server_infra

router = APIRouter()

@router.get(
    path="",
    summary="테스트 서버에 배포되어있는 pod 정보 조회",
    description="pod의 이름, 설정 자원량, openapi_spec 연결 정보, 라벨 정보를 반환한다."
)
async def get_pods_info_list(
        db: AsyncSession = Depends(get_async_db)
):
    response = await build_response_get_pods_info_list(db)
    return response

@router.patch(
    path="",
    summary="openapi_spec과 server_infra 연결 API",
    description="""
        특정 openapi_spec에 대해서 테스트를 진행할 때 
        
        자원 수집량을 비교할 server_infra를 연결하는 기능 수행 

    """
)
async def connect_openapi_spec_and_server_infra(
    request: ConnectOpenAPIInfraRequest,
    db: AsyncSession = Depends(get_async_db)
):
    if not request.openapi_spec_id:
        raise ApiException(FailureCode.BAD_REQUEST, "open api spec id is null")

    if not request.server_infra_id:
        raise ApiException(FailureCode.BAD_REQUEST, "server infra id is null")

    await update_connection_openapi_spec_and_server_infra(db, request)
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE)