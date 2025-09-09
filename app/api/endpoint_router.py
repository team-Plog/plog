from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.models import get_db
from app.models.sqlite.models.project_models import EndpointModel
from app.common.response.code import SuccessCode, FailureCode
from app.common.response.response_template import ResponseTemplate

router = APIRouter()

@router.delete(
    path="/{endpoint_id}",
    summary="엔드포인트 삭제 API",
    description="""
    지정한 ID를 가진 엔드포인트를 삭제하는 API입니다.
    
    ## 삭제 대상:
    - 해당 엔드포인트 정보
    - 태그와 엔드포인트 간의 연결관계 (many-to-many)
    
    ## 참고사항:
    - 해당 엔드포인트를 사용하는 테스트 히스토리의 시나리오 정보는 유지됩니다
    - 삭제 후 복구가 불가능하므로 신중하게 사용하세요
    - 엔드포인트를 참조하는 부하테스트 실행 시 오류가 발생할 수 있습니다
    """
)
async def delete_endpoint(
    endpoint_id: int = Path(..., description="삭제할 엔드포인트의 ID"),
    db: Session = Depends(get_db)
):
    # 엔드포인트 조회
    endpoint = db.query(EndpointModel).filter(EndpointModel.id == endpoint_id).first()
    
    if not endpoint:
        return ResponseTemplate.fail(FailureCode.NOT_FOUND_DATA)
    
    # 엔드포인트 삭제 (many-to-many 관계도 자동으로 정리됨)
    db.delete(endpoint)
    db.commit()
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE)

@router.get(
    path="",
    summary="엔드포인트 리스트 조회 API",
    description="저장된 모든 엔드포인트를 리스트 형태로 반환합니다."
)
async def get_endpoints(
    db: Session = Depends(get_db)
):
    # DB에서 모든 EndpointModel 조회
    endpoints = db.query(EndpointModel).all()
    
    # 응답 데이터 구성
    response = [
        {
            "id": endpoint.id,
            "path": endpoint.path,
            "method": endpoint.method,
            "summary": endpoint.summary,
            "description": endpoint.description,
            "tag_count": len(endpoint.tags) if endpoint.tags else 0
        }
        for endpoint in endpoints
    ]
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.get(
    path="/{endpoint_id}",
    summary="엔드포인트 상세 조회 API",
    description="지정한 ID의 엔드포인트 상세 정보를 조회합니다."
)
async def get_endpoint(
    endpoint_id: int = Path(..., description="조회할 엔드포인트의 ID"),
    db: Session = Depends(get_db)
):
    # 엔드포인트 조회 (태그 정보 포함)
    endpoint = db.query(EndpointModel).filter(EndpointModel.id == endpoint_id).first()
    
    if not endpoint:
        return ResponseTemplate.fail(FailureCode.NOT_FOUND_DATA)
    
    # 응답 데이터 구성
    response = {
        "id": endpoint.id,
        "path": endpoint.path,
        "method": endpoint.method,
        "summary": endpoint.summary,
        "description": endpoint.description,
        "tags": [
            {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description
            }
            for tag in endpoint.tags
        ] if endpoint.tags else []
    }
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)