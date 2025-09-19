from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode
from app.models.sqlite.models import ServerInfraModel, OpenAPISpecModel
from app.schemas.infra import ConnectOpenAPIInfraRequest
from k8s.pod_service import PodService
from k8s.resource_service import ResourceService
from k8s.service_service import ServiceService


async def build_response_get_pods_info_list(
        db: AsyncSession
):
    resource_service = ResourceService()
    pod_service = PodService()
    service_service = ServiceService()

    responses = []
    stmt = select(ServerInfraModel)
    result = await db.execute(stmt)
    server_infras = result.scalars().all()


    for server_infra in server_infras:
        pod_name = server_infra.name
        resource_specs = resource_service.get_pod_aggregated_resources(pod_name)
        pod_info = pod_service.get_pod_details_with_owner_info(pod_name)

        if not pod_info:
            continue

        # 하나의 배포 단위 당 하나의 service가 존재한다고 가정
        services = pod_service.find_services_for_pod(pod_info["labels"])

        if not services:
            continue

        service = services[0]
        response = {
            "server_infra_id": server_infra.id,
            "openapi_spec_id": server_infra.openapi_spec_id,
            "pod_name": pod_info,
            "resource_type": server_infra.resource_type,
            "service_type": server_infra.service_type,
            "group_name": server_infra.group_name,
            "label": server_infra.label,
            "namespace": server_infra.namespace,
            "resource_specs": resource_specs,
            "service_info": {
                "port": service["ports"],
                "node_port": service["node_ports"],
            }
        }

        responses.append(response)

    return responses

async def update_connection_openapi_spec_and_server_infra(
        db: AsyncSession,
        request: ConnectOpenAPIInfraRequest
):
    stmt = select(ServerInfraModel).where(ServerInfraModel.group_name == request.group_name)
    result = await db.execute(stmt)
    server_infras = result.scalars().all()


    if not server_infras:
        raise ApiException(FailureCode.NOT_FOUND_DATA, "Not Found Server Infra")

    stmt = select(OpenAPISpecModel).where(OpenAPISpecModel.id == request.openapi_spec_id)
    openapi_spec = await db.scalar(stmt)

    if not openapi_spec:
        raise ApiException(FailureCode.NOT_FOUND_DATA, "Not Found OpenAPI Spec")

    for server_infra in server_infras:
        server_infra.openapi_spec_id = request.openapi_spec_id

    await db.commit()