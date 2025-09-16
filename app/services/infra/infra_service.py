from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode
from app.models.sqlite.models import ServerInfraModel, OpenAPISpecModel
from app.schemas.infra import ConnectOpenAPIInfraRequest


async def build_response_get_pods_info_list(
        db: AsyncSession
):
    stmt = select(ServerInfraModel)
    result = await db.execute(stmt)
    server_infras = result.scalars().all()

    return server_infras

async def update_connection_openapi_spec_and_server_infra(
        db: AsyncSession,
        request: ConnectOpenAPIInfraRequest
):
    stmt = select(ServerInfraModel).where(ServerInfraModel.id == request.server_infra_id)
    server_infra = await db.scalar(stmt)

    if not server_infra:
        raise ApiException(FailureCode.NOT_FOUND_DATA, "Not Found Server Infra")

    stmt = select(OpenAPISpecModel).where(OpenAPISpecModel.id == request.openapi_spec_id)
    openapi_spec = await db.scalar(stmt)

    if not openapi_spec:
        raise ApiException(FailureCode.NOT_FOUND_DATA, "Not Found OpenAPI Spec")

    server_infra.openapi_spec_id = request.openapi_spec_id
    await db.commit()