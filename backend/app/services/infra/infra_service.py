import logging
from typing import Dict, Any

from kubernetes.client import V1Deployment
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
from k8s.deploy_service import DeployService
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
    deploy_service = DeployService()
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

    # Git hooks 없이 배포된 경우 version detail 자동 생성
    if not version_detail:
        logger.warning(f"Version detail not found for {request.group_name}, creating default detail from deployment")

        try:
            # ServerInfra의 name을 deployment 이름으로 사용
            pod_name = first_server_infra.name
            namespace = first_server_infra.namespace or "test"

            # DeployService를 통해 version detail 생성 및 저장
            version_detail = await create_and_save_version_detail(
                db=db,
                openapi_spec_version_id=openapi_spec_version.id,
                pod_name=pod_name,
                namespace=namespace
            )

            logger.info(f"Successfully created version detail for {request.group_name}")

        except Exception as e:
            logger.error(f"Failed to create version detail for {request.group_name}: {e}")
            raise ApiException(FailureCode.INTERNAL_SERVER_ERROR, f"Version detail 생성에 실패했습니다: {str(e)}")

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
                    "request": current_resource_info["requests"]["cpu"],
                    "limit": current_resource_info["limits"]["cpu"],
                },
                "memory": {
                    "request": current_resource_info["requests"]["memory"],
                    "limit": current_resource_info["limits"]["memory"],
                }
            }
        },
        "current": {
            "replicas": request.replicas,
            "resource_usage": {
                "cpu": {
                    "request": updated_resource_info["requests"]["cpu"],
                    "limit": updated_resource_info["limits"]["cpu"],
                },
                "memory": {
                    "request": updated_resource_info["requests"]["memory"],
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
        current_resource_info["requests"]["cpu"] = "null"
    else:
        current_resource_info["requests"]["cpu"] = update_resource_info.cpu_request_millicores

    if update_resource_info.memory_request_millicores is None:
        current_resource_info["requests"]["memory"] = "null"
    else:
        current_resource_info["requests"]["memory"] = update_resource_info.memory_request_millicores

    if update_resource_info.cpu_limit_millicores is None:
        current_resource_info["limits"]["cpu"] = "null"
    else:
        current_resource_info["limits"]["cpu"] = update_resource_info.cpu_limit_millicores

    if update_resource_info.memory_limit_millicores is None:
        current_resource_info["limits"]["memory"] = "null"
    else:
        current_resource_info["limits"]["memory"] = update_resource_info.memory_limit_millicores

    return current_resource_info

async def create_and_save_version_detail(
             db,
             openapi_spec_version_id: int,
             pod_name: str,
             namespace: str = "test"
):
    """
    Pod 이름으로부터 Deployment를 찾아서 OpenAPISpecVersionDetail을 생성하고 DB에 저장

    Args:
        db: 데이터베이스 세션
        openapi_spec_version_id (int): OpenAPI Spec Version ID
        pod_name (str): Pod 이름
        namespace (str): 네임스페이스

    Returns:
        OpenAPISpecVersionDetailModel: 생성된 version detail 객체
    """
    deploy_service = DeployService()
    service_service = ServiceService()
    from app.models.sqlite.models import OpenAPISpecVersionDetailModel

    # Pod에서 Deployment 이름 찾기
    deployment_name = deploy_service.find_deployment_name_from_pod(pod_name, namespace)

    if not deployment_name:
        raise Exception(f"Could not find deployment for pod: {pod_name}")

    # Deployment 정보로부터 detail 추출
    deployment: V1Deployment = deploy_service.get_deployment_details(deployment_name, namespace)
    deploy_dict = deployment.to_dict()

    logger.info(f"Deployment dict keys: {deploy_dict.keys()}")
    logger.info(f"Spec keys: {deploy_dict.get('spec', {}).keys()}")
    logger.info(f"Selector: {deploy_dict.get('spec', {}).get('selector', {})}")

    image_url = deploy_dict["spec"]["template"]["spec"]["containers"][0]["image"]
    logger.info(f"Image URL: {image_url}")

    repo_part, image_tag = image_url.rsplit(":", 1)
    registry, repository = repo_part.split("/", 1)


    # match_labels 키 확인 후 접근
    selector = deploy_dict.get("spec", {}).get("selector", {})
    labels = selector.get("match_labels") or selector.get("matchLabels", {})

    logger.info(f"Extracted labels: {labels}")

    services = service_service.get_service_by_labels(labels)
    service = services[0]

    # app_name 추출 (metadata에서)
    app_name = deploy_dict.get("metadata", {}).get("labels", {}).get("app", deployment_name)

    # replicas 추출
    replicas = deploy_dict.get("spec", {}).get("replicas", 1)

    # OpenAPISpecVersionDetail 객체 생성 (namespace 제거)
    version_detail = OpenAPISpecVersionDetailModel(
        openapi_spec_version_id=openapi_spec_version_id,
        image_registry_url=registry,
        app_name=app_name,
        replicas=replicas,
        node_port=service["ports"][0].get("node_port"),
        port=service["ports"][0]["port"],
        image_tag=image_tag,
        git_info=None,
        resources=deployment.spec.template.spec.containers[0].resources.to_dict() if deployment.spec.template.spec.containers[0].resources else {},
        volumes={},  # PlogConfigDTO는 dict를 기대
        env={env.name: env.value for env in (deployment.spec.template.spec.containers[0].env or [])},  # dict 형태로 변환
    )

    db.add(version_detail)
    await db.commit()
    await db.refresh(version_detail)

    logger.info(f"Created version detail for deployment: {deployment_name}, version_id: {openapi_spec_version_id}")
    return version_detail