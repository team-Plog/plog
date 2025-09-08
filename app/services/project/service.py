import logging
from sqlalchemy.orm import Session
from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode
from app.db.sqlite.models import ProjectModel, EndpointModel

logger = logging.getLogger(__name__)

def get_project_by_endpoint_id_simple(db: Session, endpoint_id: int) -> ProjectModel:
    """endpoint_id로 프로젝트 조회 - 관계 활용"""
    endpoint = db.query(EndpointModel).filter(EndpointModel.id == endpoint_id).first()

    if endpoint.openapi_spec_version.openapi_spec.project:
        # 첫 번째 태그의 openapi_spec을 통해 프로젝트 조회
        return endpoint.openapi_spec_version.openapi_spec.project

    raise ApiException(FailureCode.NOT_FOUND_DATA, f"Endpoint {endpoint_id} not found")