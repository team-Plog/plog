import logging
from fastapi import APIRouter, Depends, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.models import get_db, get_async_db
from app.models.sqlite.models.project_models import OpenAPISpecModel, OpenAPISpecVersionModel
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.schemas.openapi_spec.plog_deploy_request import PlogConfigDTO

from app.schemas.project.openapi import OpenAPISpec
from app.common.response.code import SuccessCode, FailureCode
from app.common.response.response_template import ResponseTemplate
from app.services import *
from app.services.openapi.strategy_factory import analyze_openapi_with_strategy
from app.services.openapi.openapi_service import deploy_openapi_spec as deploy_openapi_spec_service, \
    build_response_openapi_spec_version_list, process_openapi_spec_version_update

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    path="/analyze",
    summary="서버 저장 API",
    description="openapi url를 통해 애플리케이션 openapi 정보(버전, 설명, 엔드포인트)를 프로젝트에 저장한다.",
)
async def analyze_swagger(
    request: OpenAPISpecRegisterRequest,
    db: Session = Depends(get_db)
):
    # 1. analyze using strategy pattern
    analyze_result: OpenAPISpecModel = await analyze_openapi_with_strategy(request=request, db=db)

    # 2. save
    saved_open_api_spec: OpenAPISpecModel = save_openapi_spec(db, analyze_result)

    response = {
        "id": saved_open_api_spec.id,
        "title": saved_open_api_spec.title,
        "version": saved_open_api_spec.version,
        "base_url": saved_open_api_spec.base_url,
    }

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.get(
    path="",
    summary="OpenAPI 명세 리스트 조회 API",
    description="저장된 OpenAPI 명세들을 리스트 형태로 반환한다."
)
async def get_openapi_specs(
    db: Session = Depends(get_db)
):
    stmt = (
        select(
            OpenAPISpecModel.id,
            OpenAPISpecModel.title,
            OpenAPISpecModel.version,
            OpenAPISpecModel.base_url,
            OpenAPISpecVersionModel.commit_hash,
            OpenAPISpecVersionModel.created_at
        )
        .join(
            OpenAPISpecVersionModel,
            (OpenAPISpecVersionModel.open_api_spec_id == OpenAPISpecModel.id)
            & (OpenAPISpecVersionModel.is_activate == True)  # ✅ 활성화 버전만
        )
    )

    result = db.execute(stmt)
    response = result.mappings().all()

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.delete(
    path="/{openapi_spec_id}",
    summary="OpenAPI 명세 삭제 API",
    description="""
    지정한 ID를 가진 OpenAPI 명세(서버)를 삭제하는 API.
    
    ## 삭제 대상:
    - OpenAPI 명세 정보
    - 해당 명세에 속한 모든 태그
    - 태그와 연결된 모든 엔드포인트 (cascade 삭제)
    
    ## 참고사항:
    - 삭제된 OpenAPI 명세와 관련된 테스트 히스토리는 유지
    """
)
async def delete_openapi_spec(
    openapi_spec_id: int = Path(..., description="삭제할 OpenAPI 명세의 ID"),
    db: Session = Depends(get_db)
):
    # OpenAPI 명세 조회
    openapi_spec = db.query(OpenAPISpecModel).filter(OpenAPISpecModel.id == openapi_spec_id).first()
    
    if not openapi_spec:
        return ResponseTemplate.fail(FailureCode.NOT_FOUND_DATA)
    
    # cascade 삭제로 인해 관련된 태그와 엔드포인트도 함께 삭제됨
    db.delete(openapi_spec)
    db.commit()
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE)

@router.post(
    path="/deploy",
    summary="새로운 애플리케이션을 배포하거나 업데이트 하는 API",
    description="""
        로컬 프로젝트 루트 디렉터리에 저장된 plog.json 파일 데이터를 통해 배포하는 API 
        
        쿠버네티스 패키징 도구 Helm을 통해서 애플리케이션을 아래와 같이 배포 또는 업데이트한다. 
            1. k3s 배포 환경 설정 (helm upgrade --install ~~)
            2. openapi_spec 생성 또는 새로운 버전의 openapi_spec_version 생성 
    """
)
async def deploy_openapi_spec(
    request: PlogConfigDTO,
    db: Session = Depends(get_db)
):
    try:
        # 비즈니스 로직 서비스에 위임
        result = await deploy_openapi_spec_service(db, request)
        
        return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, result)
        
    except Exception as e:
        logger.error(f"배포 중 오류 발생: {str(e)}")
        
        # 에러 상세 정보를 포함한 실패 응답
        error_data = {
            "app_name": request.app_name if hasattr(request, 'app_name') else "unknown",
            "error": str(e),
            "message": "애플리케이션 배포에 실패했습니다."
        }
        
        return ResponseTemplate.fail(FailureCode.INTERNAL_SERVER_ERROR, data=error_data)

@router.get(
    path="/{openapi_spec_id}/versions",
    summary="서버 버전 리스트 조회 API",
    description="등록된 서버의 현재 버전을 포함한 과거 버전 정보 리스트를 반환합니다."
)
async def get_openapi_spec_version_list(
        openapi_spec_id: int = Path(..., title="openapi_spec의 ID", ge=1),
        db: AsyncSession = Depends(get_async_db)
):
    response = await build_response_openapi_spec_version_list(db, openapi_spec_id)
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.patch(
    path="/versions/{openapi_spec_version_id}",
    summary="서버 버전 변경 API",
    description="""
    선택한 version id로 openapi_spec의 버전을 변경합니다.
    """
)
async def update_openapi_spec_version(
        openapi_spec_version_id: int = Path(..., title="openapi_spec_version의 ID", ge=1),
        db: AsyncSession = Depends(get_async_db)
):
    await process_openapi_spec_version_update(db, openapi_spec_version_id)

    pass