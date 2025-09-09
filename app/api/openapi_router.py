from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.models import get_db
from app.models.sqlite.models.project_models import OpenAPISpecModel
from app.schemas.open_api_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest

from app.schemas.project.openapi import OpenAPISpec
from app.common.response.code import SuccessCode, FailureCode
from app.common.response.response_template import ResponseTemplate
from app.services import *
from app.services.openapi.strategy_factory import analyze_openapi_with_strategy

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
    analyze_result: OpenAPISpecModel = await analyze_openapi_with_strategy(request)

    # 2. save
    saved_open_api_spec: OpenAPISpecModel = await save_openapi_spec(db, analyze_result)

    # 3. converter
    response = OpenAPISpec.from_orm(saved_open_api_spec).model_dump()

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.get(
    path="",
    summary="OpenAPI 명세 리스트 조회 API",
    description="저장된 OpenAPI 명세들을 리스트 형태로 반환한다."
)
async def get_openapi_specs(
    db: Session = Depends(get_db)
):
    # DB에서 모든 OpenAPISpecModel 조회
    openapi_specs = db.query(OpenAPISpecModel).all()

    # Pydantic 모델로 변환
    response = [OpenAPISpec.from_orm(spec).model_dump() for spec in openapi_specs]

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