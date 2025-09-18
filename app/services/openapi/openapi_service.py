import os
import logging
import asyncio
from urllib.parse import urlparse

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.sqlite.models import OpenAPISpecVersionDetailModel
from app.models.sqlite.models.project_models import OpenAPISpecModel, OpenAPISpecVersionModel, EndpointModel, ParameterModel
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.schemas.openapi_spec.plog_deploy_request import PlogConfigDTO
from app.dto.openapi_parse_result import OpenAPIParseResult
from app.services.openapi.strategy_factory import create_openapi_analysis_context
from app.utils.url_converter import convert_localhost_to_service_url, is_localhost_url
from app.utils.helm_executor import HelmExecutor
from app.utils.helm_values_generator import HelmValuesGenerator
from app.utils.file_writer import FileWriter
from k8s.service_service import ServiceService
from k8s.pod_service import PodService
from app.core.config import settings

logger = logging.getLogger(__name__)


async def analyze_openapi_with_strategy(
    request: OpenAPISpecRegisterRequest,
    db: Session = None,
    convert_url: bool = True,
    conversion_mappings: Optional[Dict[str, Dict[str, str]]] = None
) -> OpenAPISpecModel:
    """
    전략 패턴을 사용하여 OpenAPI를 분석하고 비즈니스 로직을 처리합니다.

    Args:
        request: OpenAPI 스펙 등록 요청 객체
        db: 데이터베이스 세션
        convert_url: localhost URL을 service URL로 변환할지 여부
        conversion_mappings: URL 변환 매핑 정보 (server_pod_scheduler 호환)

    Returns:
        OpenAPISpecModel: 완성된 OpenAPI 스펙 모델
    """
    try:
        # 1. 전략 패턴으로 파싱 수행
        logger.info(f"전략 분석 컨텍스트 생성 시작: {request.open_api_url}")
        context = await create_openapi_analysis_context(request)
        logger.info(f"OpenAPI 파싱 시작: {request.open_api_url}")
        parse_result = await context.parse(request)
        logger.info(f"OpenAPI 파싱 완료: title={parse_result.title}, base_url={parse_result.base_url}, endpoints={len(parse_result.endpoints)}")

        # 2. URL 변환 로직 (일관성 확보)
        if convert_url and is_localhost_url(parse_result.base_url):
            if conversion_mappings:
                from app.utils.url_converter import convert_url_with_mapping
                original_base_url = parse_result.base_url
                converted_base_url = convert_url_with_mapping(parse_result.base_url, conversion_mappings)

                if converted_base_url != original_base_url:
                    parse_result.base_url = converted_base_url
                    logger.info(f"URL 변환 완료: {original_base_url} → {converted_base_url}")
                else:
                    logger.warning(f"URL 변환 실패: {original_base_url} (매핑 정보 없음)")

            else:
                logger.info(f"localhost URL 감지되었지만 변환 매핑이 없음: {parse_result.base_url}")

        # 3. DB 비즈니스 로직
        return await create_openapi_spec_from_parse_result(parse_result, request, db)

    except Exception as e:
        logger.error(f"OpenAPI 파싱 중 오류 발생: {str(e)}")
        import traceback
        logger.error(f"파싱 에러 상세 정보: {traceback.format_exc()}")
        raise


async def create_openapi_spec_from_parse_result(
    parse_result: OpenAPIParseResult,
    request: OpenAPISpecRegisterRequest,
    db: Session = None
) -> OpenAPISpecModel:
    """
    파싱 결과를 바탕으로 OpenAPISpecModel을 생성합니다.

    Args:
        parse_result: 파싱된 OpenAPI 데이터
        request: 원본 요청 객체
        db: 데이터베이스 세션

    Returns:
        OpenAPISpecModel: 완성된 OpenAPI 스펙 모델
    """
    if not db:
        # DB 없이는 비즈니스 로직 처리 불가
        raise ValueError("데이터베이스 세션이 필요합니다")

    # 1. 동일한 base_url을 가진 openapi_spec이 존재하는지 확인
    existing_spec = db.query(OpenAPISpecModel).filter(
        OpenAPISpecModel.base_url == parse_result.base_url,
        OpenAPISpecModel.project_id == request.project_id
    ).first()

    # 2. 존재하면 기존 것을 사용, 없으면 새로 생성
    if existing_spec:
        openapi_spec_model = existing_spec
        logger.info(f"기존 OpenAPI 스펙 사용: {existing_spec.id}")
    else:
        openapi_spec_model = OpenAPISpecModel(
            title=parse_result.title,
            version=parse_result.version,
            base_url=parse_result.base_url,
            project_id=request.project_id,
        )
        logger.info(f"새 OpenAPI 스펙 생성: {parse_result.title}")

    # 3. OpenAPI 스펙 버전 생성
    if existing_spec:
        # 기존 버전들을 모두 비활성화
        db.query(OpenAPISpecVersionModel).filter(
            OpenAPISpecVersionModel.open_api_spec_id == existing_spec.id
        ).update({"is_activate": False})
        logger.info(f"기존 버전들 비활성화: spec_id={existing_spec.id}")

    openapi_spec_version = OpenAPISpecVersionModel(
        created_at=datetime.now(),
        commit_hash=getattr(request, 'commit_hash', None),
        is_activate=True,
        open_api_spec_id=openapi_spec_model.id if existing_spec else None
    )

    # 4. endpoint 저장 & 파라미터 파싱 (반정규화된 구조)
    all_endpoints = []

    for endpoint_data in parse_result.endpoints:
        endpoint_model = EndpointModel(
            path=endpoint_data.path,
            method=endpoint_data.method,
            summary=endpoint_data.summary,
            description=endpoint_data.description,
            tag_name=endpoint_data.tag_name,
            tag_description=endpoint_data.tag_description,
            openapi_spec_version_id=None  # 나중에 설정
        )

        # 파라미터 모델 생성
        parameters = []
        for param_data in endpoint_data.parameters:
            parameter_model = ParameterModel(
                param_type=param_data.get("param_type", ""),
                name=param_data.get("name", ""),
                required=param_data.get("required", False),
                value_type=param_data.get("value_type", ""),
                title=param_data.get("title", ""),
                description=param_data.get("description", ""),
                value=param_data.get("value")
            )
            parameters.append(parameter_model)

        # endpoint에 파라미터 연결
        endpoint_model.parameters = parameters
        all_endpoints.append(endpoint_model)

    # 5. endpoints를 openapi_spec_version에 연결
    for endpoint in all_endpoints:
        endpoint.openapi_spec_version = openapi_spec_version
    openapi_spec_version.endpoints = all_endpoints

    # 6. openapi_spec_version을 openapi_spec에 연결
    if not existing_spec:
        openapi_spec_model.openapi_spec_versions = [openapi_spec_version]
    else:
        openapi_spec_model.openapi_spec_versions.append(openapi_spec_version)

    logger.info(f"OpenAPI 스펙 처리 완료: {len(all_endpoints)}개 엔드포인트")
    return openapi_spec_model


def save_openapi_spec(db: Session, openapi_spec_model: OpenAPISpecModel) -> OpenAPISpecModel:
    db.add(openapi_spec_model)
    db.commit()
    db.refresh(openapi_spec_model)

    return openapi_spec_model



async def deploy_openapi_spec(db: Session, request: PlogConfigDTO) -> dict:
    """
    PlogConfigDTO를 받아서 배포 프로세스를 실행하는 서비스
    
    Args:
        db: 데이터베이스 세션
        request: PlogConfigDTO 배포 요청 데이터
        
    Returns:
        dict: 배포 결과 정보
        
    Raises:
        EnvironmentError: PLOG_HELM_CHART_FOLDER 환경변수가 없을 때
        Exception: 배포 프로세스 실패시
    """
    try:
        logger.info(f"1. 배포 프로세스 시작: {request.app_name}")
        
        # 1. PlogConfigDTO를 Helm values.yaml로 변환
        helm_generator = HelmValuesGenerator()
        values_yaml_content = helm_generator.generate_values_yaml(request)
        
        # 2. PLOG_HELM_CHART_FOLDER 환경변수에서 경로 가져오기
        helm_chart_folder = os.getenv("PLOG_HELM_CHART_FOLDER")
        if not helm_chart_folder:
            raise EnvironmentError("PLOG_HELM_CHART_FOLDER 환경변수가 설정되지 않았습니다.")
        
        # 3. 기존 values.yaml 파일 확인 및 제거
        from pathlib import Path
        target_file_path = str(Path(helm_chart_folder) / "values.yaml")
        
        if FileWriter.file_exists(target_file_path):
            FileWriter.remove_file(target_file_path)

        # 4. values.yaml 파일 저장
        saved_path = FileWriter.write_to_path(
            content=values_yaml_content,
            filename="values.yaml",
            base_path=helm_chart_folder,
        )
        
        logger.info(f"2. values.yaml 파일 업데이트 완료: {saved_path}")
        # ex) app_name = semi-medeasy -> service_name = semi_medeasy_service
        helm_executor = HelmExecutor()
        deployment_result = await helm_executor.upgrade_install(
            chart_path=helm_chart_folder,
            app_name=request.app_name,
            namespace="test"
        )

        logger.info(f"3. helm 패키지 배포 완료")

        # 7. 배포된 서비스 탐지 및 OpenAPI 등록
        service = ServiceService(namespace="test")
        service_label = {
            "app": request.app_name,
        }
        services_info = service.get_service_by_labels(service_label)
        service_name = services_info[0].get("name")
        service_port = services_info[0].get("ports")[0].get("port")

        logger.info(f"배포 애플리케이션 매칭 서비스 이름: {service_name}")

        # 서비스가 준비될 때까지 대기
        service_ready = await _wait_for_service_ready(service_name, timeout=60)
        if service_ready:
            logger.info(f"서비스 준비 완료: {service_name}")

            # Swagger URL 스캔 (Pod 준비 상태 확인 및 재시도 포함)
            logger.info(f"Pod 준비 상태 확인 및 Swagger URL 탐지 시작: {service_name}")
            swagger_urls = await _scan_swagger_urls_for_service(service_name)
            
            if swagger_urls:
                logger.info(f"Swagger URL 탐지됨: {swagger_urls[0]}")
                
                try:
                    # OpenAPI 등록 요청 생성
                    from pydantic import HttpUrl
                    openapi_request = OpenAPISpecRegisterRequest(
                        project_id=1,  # 기본 프로젝트 ID
                        open_api_url=HttpUrl(swagger_urls[0])
                    )


                    parsed_url = urlparse(swagger_urls[0])

                    logger.info(f"parsed_url parsing 구조 파악: {parsed_url}")

                    conversion_mappings = {
                        f"{parsed_url.scheme}://{parsed_url.netloc}": {
                            "service_name": service_name,
                            "service_port": service_port,
                        }
                    }

                    logger.info(f"변환 매핑 정보 생성: {conversion_mappings}")

                    # OpenAPI 분석 및 등록 (상세 로깅)
                    logger.info(f"OpenAPI 분석 시작: {swagger_urls[0]}")

                    analysis_result: OpenAPISpecModel = await analyze_openapi_with_strategy(
                        openapi_request,
                        db=db,
                        convert_url=True,
                        conversion_mappings=conversion_mappings
                    )

                    for version in analysis_result.openapi_spec_versions:
                        if version.is_activate == 1:
                            version.commit_hash = request.image_tag
                            version_detail = convertOpenAPISpecDetailDtoToModel(request, version.id)

                    logger.info(f"OpenAPI 분석 완료: {analysis_result}")

                    if analysis_result:
                        saved_openapi_spec = save_openapi_spec(db, analysis_result)
                        logger.info(f"OpenAPI 등록 성공: spec_id={saved_openapi_spec.id}")

                except Exception as e:
                    import traceback
                    logger.error(f"OpenAPI 등록 중 오류 발생: {str(e)}")
                    logger.error(f"상세 에러 정보: {traceback.format_exc()}")
        
        logger.info(f"배포 프로세스 완료: {request.app_name}")
        return None
        
    except Exception as e:
        logger.error(f"배포 프로세스 실패 - app: {request.app_name}, error: {str(e)}")
        raise Exception(f"배포 프로세스에 실패했습니다: {str(e)}")


async def _wait_for_service_ready(service_name: str, timeout: int = 60) -> bool:
    """
    지정된 서비스가 준비될 때까지 폴링으로 대기
    
    Args:
        service_name: 대기할 서비스 이름
        timeout: 최대 대기 시간(초)
        
    Returns:
        bool: 서비스 준비 완료 여부
    """
    service_service = ServiceService(namespace=settings.KUBERNETES_TEST_NAMESPACE)
    check_interval = 5  # 5초마다 확인
    max_attempts = timeout // check_interval
    
    logger.info(f"서비스 준비 확인 시작: {service_name} (최대 {timeout}초 대기)")
    
    for attempt in range(max_attempts):
        try:
            services = service_service.get_services()
            service_names = [svc["name"] for svc in services if svc["cluster_ip"] != "None"]
            
            if service_name in service_names:
                logger.info(f"서비스 준비 완료 확인됨: {service_name} (시도 {attempt + 1}/{max_attempts})")
                return True
                
            logger.debug(f"서비스 준비 대기 중: {service_name} (시도 {attempt + 1}/{max_attempts})")
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            logger.warning(f"서비스 상태 확인 중 오류: {str(e)} (시도 {attempt + 1}/{max_attempts})")
            await asyncio.sleep(check_interval)
    
    logger.warning(f"서비스 준비 실패: {service_name} ({timeout}초 초과)")
    return False


async def _scan_swagger_urls_for_service(service_name: str) -> List[str]:
    """
    특정 서비스의 Swagger URL을 스캔 (Pod 준비 상태 확인 및 재시도 포함)

    Args:
        service_name: 스캔할 서비스 이름

    Returns:
        List[str]: 발견된 Swagger URL 리스트
    """
    service_service = ServiceService(namespace=settings.KUBERNETES_TEST_NAMESPACE)
    pod_service = PodService(namespace=settings.KUBERNETES_TEST_NAMESPACE)

    try:
        # 서비스와 매칭되는 Pod 목록 조회
        pod_names = service_service.get_pod_names_matching_service(service_name)

        if not pod_names:
            logger.warning(f"서비스에 매칭되는 Pod이 없음: {service_name}")
            return []

        logger.info(f"발견된 Pod 목록: {pod_names}")

        # SERVER 타입 Pod 찾기
        server_pods_found = []
        for pod_name in pod_names:
            try:
                detailed_pod_info = pod_service.get_pod_details_with_owner_info(pod_name)

                if detailed_pod_info.get("service_type") == "SERVER":
                    logger.info(f"SERVER Pod 발견: {pod_name}")
                    server_pods_found.append(pod_name)

                    # Pod 준비 상태 확인 및 대기
                    if not await _wait_for_pod_ready(pod_name, pod_service, timeout=60):
                        logger.warning(f"Pod {pod_name}이 준비되지 않음 - Swagger 탐지 건너뜀")
                        continue

                    # Pod의 레이블을 사용하여 서비스 찾기
                    services = pod_service.find_services_for_pod(detailed_pod_info["labels"])
                    logger.info(f"Pod {pod_name}에 대응하는 서비스 수: {len(services)}")

                    if services:
                        # Swagger URL 탐지 (재시도 로직 포함)
                        swagger_urls = await _discover_swagger_urls_with_retry(services, max_retries=3)
                        logger.info(f"Pod {pod_name}에서 탐지된 Swagger URL 수: {len(swagger_urls)}")

                        if swagger_urls:
                            logger.info(f"Swagger URL 발견: {swagger_urls}")
                            return swagger_urls
                    else:
                        logger.warning(f"Pod에 대응하는 서비스를 찾을 수 없음: {pod_name}")

            except Exception as e:
                logger.error(f"Pod 정보 조회 오류: {pod_name}, error: {str(e)}")
                continue

        if server_pods_found:
            logger.warning(f"SERVER Pod은 찾았지만 접근 가능한 Swagger URL을 찾을 수 없음. 발견된 SERVER Pod: {server_pods_found}")
        else:
            logger.warning(f"SERVER 타입 Pod을 찾을 수 없음: {service_name}")
        return []

    except Exception as e:
        logger.error(f"Swagger URL 스캔 오류: {service_name}, error: {str(e)}")
        return []


async def _wait_for_pod_ready(pod_name: str, pod_service: PodService, timeout: int = 60) -> bool:
    """
    Pod가 준비될 때까지 대기

    Args:
        pod_name: 대기할 Pod 이름
        pod_service: PodService 인스턴스
        timeout: 최대 대기 시간(초)

    Returns:
        bool: Pod 준비 완료 여부
    """
    check_interval = 5  # 5초마다 확인
    max_attempts = timeout // check_interval

    logger.info(f"Pod 준비 상태 확인 시작: {pod_name} (최대 {timeout}초 대기)")

    for attempt in range(max_attempts):
        try:
            if pod_service.is_pod_ready(pod_name):
                logger.info(f"Pod 준비 완료: {pod_name} (시도 {attempt + 1}/{max_attempts})")
                return True

            logger.debug(f"Pod 준비 대기 중: {pod_name} (시도 {attempt + 1}/{max_attempts})")
            await asyncio.sleep(check_interval)

        except Exception as e:
            logger.warning(f"Pod 상태 확인 중 오류: {str(e)} (시도 {attempt + 1}/{max_attempts})")
            await asyncio.sleep(check_interval)

    logger.warning(f"Pod 준비 실패: {pod_name} ({timeout}초 초과)")
    return False


async def _discover_swagger_urls_with_retry(services: List[Dict[str, Any]], max_retries: int = 3) -> List[str]:
    """
    서비스 정보를 기반으로 Swagger URL을 탐지하고, 실패 시 재시도

    Args:
        services: Service 정보 리스트
        max_retries: 최대 재시도 횟수

    Returns:
        발견된 Swagger URL 리스트
    """
    for attempt in range(max_retries):
        try:
            swagger_urls = await _discover_swagger_urls_with_fallback(services)

            if swagger_urls:
                logger.info(f"Swagger URL 탐지 성공 (시도 {attempt + 1}/{max_retries}): {swagger_urls}")
                return swagger_urls

            logger.debug(f"Swagger URL 탐지 실패, 재시도 예정 (시도 {attempt + 1}/{max_retries})")

            # 마지막 시도가 아닌 경우 잠시 대기
            if attempt < max_retries - 1:
                await asyncio.sleep(10)  # 10초 대기

        except Exception as e:
            logger.warning(f"Swagger URL 탐지 중 오류 (시도 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(10)

    logger.warning(f"모든 재시도 실패: Swagger URL을 찾을 수 없음 ({max_retries}회 시도)")
    return []


async def _discover_swagger_urls_with_fallback(services: List[Dict[str, Any]]) -> List[str]:
    """
    서비스 정보를 기반으로 Swagger URL을 탐지하고, 실패 시 NodePort로 fallback 시도
    (ServerPodScheduler의 로직을 재사용)
    
    Args:
        services: Service 정보 리스트
        
    Returns:
        발견된 Swagger URL 리스트
    """
    logger.info(f"✅✅✅ discover debug services {services}")
    swagger_urls = []
    
    swagger_paths = [
        "/v3/api-docs", "/swagger-ui", "/swagger-ui/index.html",
        "/api/swagger", "/swagger", "/docs", "/api/docs",
        "/openapi.json", "/swagger.json", "/v1/api-docs",
        "/v2/api-docs", "/api-docs"
    ]
    
    for service in services:
        service_name = service["name"]
        cluster_ip = service["cluster_ip"]
        ports = service["ports"]
        service_type = service.get("type", "ClusterIP")
        
        # Try cluster internal URLs
        for port in ports:
            if _is_http_port(port):
                service_url = f"http://{service_name}.{settings.KUBERNETES_TEST_NAMESPACE}.svc.cluster.local:{port}"
                urls_found = await _check_swagger_endpoints(service_url, swagger_paths)
                swagger_urls.extend(urls_found)
                
                if cluster_ip and cluster_ip != "None":
                    cluster_url = f"http://{cluster_ip}:{port}"
                    urls_found = await _check_swagger_endpoints(cluster_url, swagger_paths)
                    swagger_urls.extend(urls_found)
        
        # NodePort fallback
        if service_type == "NodePort":
            logger.info(f"✅✅✅ nodeport fallback")
            node_ports = service.get("node_ports", [])
            port_mappings = service.get("port_mappings", {})
            await _try_nodeport_fallback(service_name, node_ports, port_mappings, swagger_paths, swagger_urls)

            # NodePort fallback에서 URL을 찾았다면 즉시 반환
            if swagger_urls:
                logger.info(f"NodePort fallback에서 Swagger URL 발견: {swagger_urls}")
                return swagger_urls
    
    return swagger_urls


async def _check_swagger_endpoints(base_url: str, swagger_paths: List[str]) -> List[str]:
    """
    주어진 base URL에 대해 swagger paths를 병렬로 확인하여 유효한 엔드포인트를 찾습니다.
    """
    potential_urls = [f"{base_url}{swagger_path}" for swagger_path in swagger_paths]
    semaphore = asyncio.Semaphore(5)
    
    async def check_single_url_with_semaphore(client, url):
        async with semaphore:
            return await _check_swagger_url_with_client(client, url)
    
    async with httpx.AsyncClient(timeout=3, follow_redirects=True) as client:
        tasks = [(asyncio.create_task(check_single_url_with_semaphore(client, url)), url) 
                for url in potential_urls]
        
        try:
            task_list = [task for task, _ in tasks]
            results = await asyncio.gather(*task_list, return_exceptions=True)
            
            for i, (result, (_, url)) in enumerate(zip(results, tasks)):
                if result is True:
                    return [url]
                    
        except Exception as e:
            logger.error(f"Error in parallel URL checking: {e}")
            raise
        
        return []


async def _try_nodeport_fallback(service_name: str, node_ports: List[int], 
                               port_mappings: Dict[int, int], swagger_paths: List[str], swagger_urls: List[str]):
    """
    NodePort 서비스에 대해 localhost로 fallback 시도
    """
    for node_port in node_ports:
        localhost_url = f"http://localhost:{node_port}"
        urls_found = await _check_swagger_endpoints(localhost_url, swagger_paths)
        
        if urls_found:
            swagger_urls.extend(urls_found)


async def _check_swagger_url_with_client(client, url: str) -> bool:
    """
    주어진 클라이언트를 사용하여 URL이 유효한 Swagger 엔드포인트인지 확인합니다.
    """
    try:
        response = await client.get(url)

        if response.status_code == 200:
            content = response.text
            content_lower = content.lower()
            swagger_keywords = [
                "swagger", "openapi", "api documentation", 
                "swagger-ui", "redoc", "rapidoc"
            ]
            keyword_found = any(keyword in content_lower for keyword in swagger_keywords)
            
            if keyword_found:
                return True
                
            # JSON 응답인 경우 OpenAPI 스펙인지 확인
            try:
                json_data = response.json()
                json_check = isinstance(json_data, dict) and (
                    "swagger" in json_data or 
                    "openapi" in json_data or 
                    "info" in json_data
                )

                if json_check:
                    return True
            except Exception:
                pass
                
    except Exception:
        pass
        
    return False


def _is_http_port(port: int) -> bool:
    """
    포트가 HTTP 서비스 포트인지 추정합니다.
    """
    common_http_ports = [80, 8080, 3000, 4000, 5000, 8000, 9000]
    return port in common_http_ports or (8000 <= port <= 9999)


async def build_response_openapi_spec_version_list(
        db: AsyncSession,
        openapi_spec_id: int
):
    stmt = select(OpenAPISpecVersionModel).where(OpenAPISpecVersionModel.open_api_spec_id == openapi_spec_id)
    result = await db.execute(stmt)
    versions = result.scalars().all()

    responses = []

    for version in versions:
        response = {
            "openapi_spec_version_id": version.id,
            "created_at": version.created_at,
            "commit_hash": version.commit_hash,
            "is_active": version.is_activate
        }
        responses.append(response)

    return responses

async def process_openapi_spec_version_update(
        db: AsyncSession,
        openapi_spec_version_id: int
):
    # version id -> openapi_spec, 현재 활성화된 version 추적
    # TODO git hooks 시 values 정보를 저장해야할 듯 -> 어디에? -> openapi_spec_version에 저장
    # TODO 버그!!! git hooks 배포를 할 때 commit_hash를 저장하지 않고 있음 ** 먼저 해결 필요 **


    # TODO 위 두개를 먼저 해결 commit_hash를 가진 image로 helm package 재배포
    # TODO 선택한 버전 is_activate=True, 현재 버전은 is_activate=False
    # TODO 응답으로는 변경되기 전 activate의 commit_hash, 변경 후 commit_hash를 첨부하면 좋을듯
    pass

def convertOpenAPISpecDetailDtoToModel(request:PlogConfigDTO, openapi_spec_version_id: int):
    model = OpenAPISpecVersionDetailModel(
        openapi_spec_version_id=openapi_spec_version_id,
        app_name=request.app_name,
        replicas=request.replicas,
        node_port=request.node_port,
        port=request.port,
        image_tag=request.image_tag,
        git_info=request.git_info,
        resources=request.resources,
        volumes=request.volumes,
        env=request.env,
    )

    return model;