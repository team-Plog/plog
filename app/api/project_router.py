from fastapi import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
from app.models import get_db
from app.models.sqlite.models import OpenAPISpecVersionModel
from app.schemas.project.openapi import ProjectResponse
from app.schemas.project.project_detail_response import ProjectDetailResponse
from app.schemas.project.project_detail_converter import ProjectDetailConverter
from app.schemas.project.register_project_request import RegisterProjectRequest
from app.models.sqlite.models.project_models import ProjectModel, OpenAPISpecModel, EndpointModel
from app.common.response.code import SuccessCode, FailureCode
from app.common.response.response_template import ResponseTemplate

router = APIRouter()

@router.post(
    path="",
    summary="프로젝트 생성",
    description="서버들을 저장하는 최상위 개념인 프로젝트를 생성하는 api",
)
async def register_project(
    request: RegisterProjectRequest,
    db: Session = Depends(get_db),
):
    project = ProjectModel(
        title=request.title,
        summary=request.summary,
        description=request.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project) # 객체 상태 새로고침

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE)

@router.get(
    path="",
    summary="프로젝트 리스트 조회",
    description="""
    홈화면에 출력되는 프로젝트 리스트를 조회하는 API, 데이터베이스에 존재하는 모든 projects를 조회한다.
    status, updated_at은 테스트 실행 구현 후 업데이트 할 예정.
    """,
)
async def get_projects(
        db: Session = Depends(get_db)
):
    projects = db.query(ProjectModel).all()
    response = [
        ProjectResponse(
            id=project.id,
            title=project.title,
            summary=project.summary,
            description=project.description,
            status=None,
            updated_at=None
        )
        for project in projects
    ]

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.get(
    path="/{project_id}",
    summary="프로젝트 상세정보 조회",
    description="프로젝트의 상세정보를 조회하는 API"
)
async def get_project_info(
    project_id: int = Path(..., description="조회할 프로젝트의 ID"),
    db: Session = Depends(get_db)
):
    project = (
        db.query(ProjectModel)
        .join(ProjectModel.openapi_specs)
        .join(OpenAPISpecModel.openapi_spec_versions)
        .filter(
            ProjectModel.id == project_id,
            OpenAPISpecVersionModel.is_activate == True
        )
        .options(
            selectinload(ProjectModel.openapi_specs)
            .selectinload(OpenAPISpecModel.openapi_spec_versions)
            .selectinload(OpenAPISpecVersionModel.endpoints)
            .selectinload(EndpointModel.parameters)
        )
        .first()
    )

    if not project:
        ResponseTemplate.fail(FailureCode.NOT_FOUND_DATA)

    # 반정규화된 구조를 기존 응답 형식으로 변환
    response = ProjectDetailConverter.convert_to_response(project)

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)

@router.delete(
    path="/{project_id}",
    summary="프로젝트 삭제 API",
    description="지정한 ID를 가진 프로젝트를 삭제하는 API"
)
async def delete_project(
    project_id: int = Path(..., description="삭제할 프로젝트의 ID"),
    db: Session = Depends(get_db),
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        ResponseTemplate.fail(FailureCode.NOT_FOUND_DATA)

    db.delete(project)
    db.commit()

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE)
