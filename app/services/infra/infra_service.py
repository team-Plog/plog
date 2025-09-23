import logging
from typing import Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, contains_eager
from sqlalchemy.orm.attributes import flag_modified

from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode
from app.models.sqlite.models import ServerInfraModel, OpenAPISpecModel, OpenAPISpecVersionModel, \
    OpenAPISpecVersionDetailModel
from app.schemas.infra import ConnectOpenAPIInfraRequest, UpdateServerInfraResourceUsageRequest
from app.schemas.openapi_spec.plog_deploy_request import PlogConfigDTO
from app.services.openapi.openapi_service import convertOpenAPISpecModelToDto, process_helm_chart
from k8s.pod_service import PodService
from k8s.resource_service import ResourceService
from k8s.service_service import ServiceService

logger = logging.getLogger(__name__)

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
        workloads = pod_service.find_workloads_for_pod(pod_info["labels"])
        workload = workloads[0]
        replica = None

        if not workload:
            replica = 1
        else:
            replica = workload.get("current_replicas", 1)

        if not services:
            continue

        service = services[0]
        response = {
            "server_infra_id": server_infra.id,
            "openapi_spec_id": server_infra.openapi_spec_id,
            "pod_name": pod_info.get("name"),
            "resource_type": server_infra.resource_type,
            "service_type": server_infra.service_type,
            "group_name": server_infra.group_name,
            "label": server_infra.label,
            "namespace": server_infra.namespace,
            "resource_specs": resource_specs,
            "replicas": replica,
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

async def process_updated_server_infra_resource_usage(
        db: AsyncSession,
        request: UpdateServerInfraResourceUsageRequest
):
    resource_service = ResourceService()
    logger.info(f"Request recived {request.model_dump()}")

    # 현재 배포되어 있는 resource info 조회
    stmt = (
        select(ServerInfraModel)
        .join(ServerInfraModel.openapi_spec)
        .join(OpenAPISpecModel.openapi_spec_versions)
        .outerjoin(OpenAPISpecVersionModel.version_detail)
        .filter(OpenAPISpecVersionModel.is_activate == True)
        .options(
            contains_eager(ServerInfraModel.openapi_spec)
            .contains_eager(OpenAPISpecModel.openapi_spec_versions)
            .contains_eager(OpenAPISpecVersionModel.version_detail)
        )
        .where(ServerInfraModel.group_name == request.group_name)
    )

    result = await db.execute(stmt)
    server_infras = result.scalars()

    first_server_infra = server_infras.first()
    logger.info(f"first_server_infra: {first_server_infra}")

    if not first_server_infra:
        # JOIN 쿼리 실패시 단순 조회로 fallback
        logger.warning(f"JOIN query failed for group_name: {request.group_name}, trying simple query")
        simple_stmt = select(ServerInfraModel).where(ServerInfraModel.group_name == request.group_name)
        simple_result = await db.execute(simple_stmt)
        simple_infras = simple_result.scalars().all()
        logger.info(f"Simple query result count: {len(simple_infras)}")
        if simple_infras:
            logger.info(f"Simple query first item openapi_spec_id: {simple_infras[0].openapi_spec_id}")

        raise ApiException(FailureCode.NOT_FOUND_DATA, f"Not Found Server Infra with active OpenAPI spec for group: {request.group_name}")

    if not first_server_infra.openapi_spec:
        raise ApiException(FailureCode.NOT_FOUND_DATA, f"OpenAPI Spec not connected to server infra group: {request.group_name}")

    openapi_spec = first_server_infra.openapi_spec
    openapi_spec_version = openapi_spec.openapi_spec_versions[0]
    version_detail: OpenAPISpecVersionDetailModel = openapi_spec_version.version_detail

    if not version_detail:
        raise ApiException(FailureCode.BAD_REQUEST, "Git hooks로 배포가 되지 않은 infra에 대해 설정 기능이 제공되지 않습니다.")

    # version_detail 현재 값 조회 및 변경
    current_replicas = version_detail.replicas
    current_resource_info: Dict[str, Any] = version_detail.resources
    updated_resource_info = update_resource_info(current_resource_info, request)
    logger.info(f"updated_resource_info: {updated_resource_info}")

    # helm chart request 생성 및 변경된 값 적용
    plog_config_dto:PlogConfigDTO = convertOpenAPISpecModelToDto(version_detail)
    plog_config_dto.resources = updated_resource_info
    plog_config_dto.replicas = request.replicas
    logger.info(f"plog_config_dto: {plog_config_dto.model_dump()}")

    # SQLAlchemy 변경 추적을 위한 명시적 처리
    version_detail.resources = updated_resource_info.copy()  # 새로운 객체로 할당

    if request.replicas >= 1:
        version_detail.replicas = request.replicas

    # 또는 flag_modified 사용 (선택적)
    flag_modified(version_detail, 'resources')
    await db.commit()

    # 변경된 resource 값으로 배포
    await process_helm_chart(plog_config_dto)

    response = {
        "past" : {
            "replicas": current_replicas,
            "resource_usage": {
                "cpu": {
                    "request": current_resource_info["request"]["cpu"],
                    "limit": current_resource_info["limits"]["cpu"],
                },
                "memory": {
                    "request": current_resource_info["request"]["memory"],
                    "limit": current_resource_info["limits"]["memory"],
                }
            }
        },
        "current": {
            "replicas": request.replicas,
            "resource_usage": {
                "cpu": {
                    "request": updated_resource_info["request"]["cpu"],
                    "limit": updated_resource_info["limits"]["cpu"],
                },
                "memory": {
                    "request": updated_resource_info["request"]["memory"],
                    "limit": updated_resource_info["limits"]["memory"],
                }
            }
        }
    }


    return response



def update_resource_info(
        current_resource_info: Dict[str, Any],
        update_resource_info: UpdateServerInfraResourceUsageRequest
) -> Dict[str, Any]:
    """
    리소스 정보를 업데이트합니다.

    Args:
        current_resource_info: 현재 리소스 정보 딕셔너리
        update_resource_info: 업데이트할 리소스 정보

    Returns:
        Dict[str, Any]: 업데이트된 리소스 정보
    """

    if update_resource_info.cpu_request_millicores is None:
        current_resource_info["request"]["cpu"] = "null"
    else:
        current_resource_info["request"]["cpu"] = update_resource_info.cpu_request_millicores

    if update_resource_info.memory_request_millicores is None:
        current_resource_info["request"]["memory"] = "null"
    else:
        current_resource_info["request"]["memory"] = update_resource_info.memory_request_millicores

    if update_resource_info.cpu_limit_millicores is None:
        current_resource_info["limits"]["cpu"] = "null"
    else:
        current_resource_info["limits"]["cpu"] = update_resource_info.cpu_limit_millicores

    if update_resource_info.memory_limit_millicores is None:
        current_resource_info["limits"]["memory"] = "null"
    else:
        current_resource_info["limits"]["memory"] = update_resource_info.memory_limit_millicores

    return current_resource_info