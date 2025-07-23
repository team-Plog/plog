from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.dto import project
from app.dto.project.openapi import ProjectResponse
from app.dto.project.register_project_request import RegisterProjectRequest
from app.db.sqlite.models import ProjectModel
from app.response.code import SuccessCode
from app.response.response_template import ResponseTemplate

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
            description=project.description,
            status=None,
            updated_at=None
        )
        for project in projects
    ]

    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response)