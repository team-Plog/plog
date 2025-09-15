import os
import logging
import asyncio
import httpx
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.sqlite.models.project_models import OpenAPISpecModel
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.schemas.openapi_spec.plog_deploy_request import PlogConfigDTO
from app.services.openapi.strategy_factory import analyze_openapi_with_strategy
from app.utils.helm_executor import HelmExecutor
from app.utils.helm_values_generator import HelmValuesGenerator
from app.utils.file_writer import FileWriter
from k8s.service_service import ServiceService
from k8s.pod_service import PodService
from app.core.config import settings

logger = logging.getLogger(__name__)


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
        logger.info(f"배포 프로세스 시작: {request.app_name}")
        
        # 1. PlogConfigDTO를 Helm values.yaml로 변환
        helm_generator = HelmValuesGenerator()
        values_yaml_content = helm_generator.generate_values_yaml(request)
        
        logger.info(f"values.yaml 생성 완료: {request.app_name}")
        
        # 2. PLOG_HELM_CHART_FOLDER 환경변수에서 경로 가져오기
        helm_chart_folder = os.getenv("PLOG_HELM_CHART_FOLDER")
        if not helm_chart_folder:
            raise EnvironmentError("PLOG_HELM_CHART_FOLDER 환경변수가 설정되지 않았습니다.")
        
        # 3. 기존 values.yaml 파일 확인 및 제거
        from pathlib import Path
        target_file_path = str(Path(helm_chart_folder) / "values.yaml")
        
        if FileWriter.file_exists(target_file_path):
            FileWriter.remove_file(target_file_path)
            logger.info(f"기존 values.yaml 파일을 제거했습니다: {target_file_path}")
        
        # 4. values.yaml 파일 저장
        saved_path = FileWriter.write_to_path(
            content=values_yaml_content,
            filename="values.yaml",
            base_path=helm_chart_folder,
        )
        
        logger.info(f"values.yaml 파일 저장 완료: {saved_path}")

        # ex) app_name = semi-medeasy -> service_name = semi_medeasy_service
        helm_executor = HelmExecutor()
        deployment_result = await helm_executor.upgrade_install(
            chart_path=helm_chart_folder,
            app_name=request.app_name,
            namespace="test"
        )

        # 7. 배포된 서비스 탐지 및 OpenAPI 등록
        expected_service_name = helm_executor.get_expected_service_name(request.app_name)
        
        logger.info(f"예상 서비스 이름: {expected_service_name}")
        
        # 서비스가 준비될 때까지 대기
        service_ready = await _wait_for_service_ready(expected_service_name, timeout=60)
        
        openapi_result = {
            "status": "not_attempted",
            "message": "OpenAPI 등록을 시도하지 않았습니다.",
            "swagger_url": None,
            "openapi_spec_id": None
        }
        
        if service_ready:
            logger.info(f"서비스 준비 완료: {expected_service_name}")
            
            # Swagger URL 스캔
            swagger_urls = await _scan_swagger_urls_for_service(expected_service_name)
            
            if swagger_urls:
                logger.info(f"Swagger URL 탐지됨: {swagger_urls[0]}")
                
                try:
                    # OpenAPI 등록 요청 생성
                    from pydantic import HttpUrl
                    openapi_request = OpenAPISpecRegisterRequest(
                        project_id=1,  # 기본 프로젝트 ID
                        open_api_url=HttpUrl(swagger_urls[0])
                    )
                    
                    # OpenAPI 분석 및 등록
                    analysis_result = await analyze_openapi_with_strategy(openapi_request)
                    
                    if analysis_result:
                        saved_openapi_spec = save_openapi_spec(db, analysis_result)
                        
                        openapi_result = {
                            "status": "success",
                            "message": "OpenAPI 등록이 완료되었습니다.",
                            "swagger_url": swagger_urls[0],
                            "openapi_spec_id": saved_openapi_spec.id
                        }
                        
                        logger.info(f"OpenAPI 등록 성공: spec_id={saved_openapi_spec.id}")
                    else:
                        openapi_result = {
                            "status": "analysis_failed",
                            "message": "OpenAPI 분석에 실패했습니다.",
                            "swagger_url": swagger_urls[0],
                            "openapi_spec_id": None
                        }
                        
                except Exception as e:
                    logger.error(f"OpenAPI 등록 중 오류 발생: {str(e)}")
                    openapi_result = {
                        "status": "registration_failed",
                        "message": f"OpenAPI 등록 중 오류가 발생했습니다: {str(e)}",
                        "swagger_url": swagger_urls[0] if swagger_urls else None,
                        "openapi_spec_id": None
                    }
            else:
                openapi_result = {
                    "status": "swagger_not_found",
                    "message": "Swagger UI URL을 찾을 수 없습니다. 수동으로 등록해주세요.",
                    "swagger_url": None,
                    "openapi_spec_id": None
                }
                logger.warning(f"Swagger URL을 찾을 수 없음: {expected_service_name}")
        else:
            openapi_result = {
                "status": "service_not_ready",
                "message": f"서비스가 60초 내에 준비되지 않았습니다: {expected_service_name}",
                "swagger_url": None,
                "openapi_spec_id": None
            }
            logger.warning(f"서비스 준비 실패: {expected_service_name}")

        # 8. 향후 확장 가능한 배포 결과 반환
        result = {
            "app_name": request.app_name,
            "helm_deployment": {
                "status": "success",
                "release_name": deployment_result.get("release_name"),
                "values_yaml_path": saved_path,
                "helm_chart_folder": helm_chart_folder,
                "message": f"{request.app_name} Helm 배포가 완료되었습니다."
            },
            "openapi_registration": openapi_result
        }
        
        logger.info(f"배포 프로세스 완료: {request.app_name}")
        return result
        
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
    특정 서비스의 Swagger URL을 스캔
    
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
        
        # SERVER 타입 Pod 찾기
        for pod_name in pod_names:
            try:
                detailed_pod_info = pod_service.get_pod_details_with_owner_info(pod_name)
                
                if detailed_pod_info.get("service_type") == "SERVER":
                    logger.info(f"SERVER Pod 발견: {pod_name}")
                    
                    # Pod의 레이블을 사용하여 서비스 찾기
                    services = pod_service.find_services_for_pod(detailed_pod_info["labels"])
                    
                    if services:
                        # Swagger URL 탐지 (ServerPodScheduler 로직 재사용)
                        swagger_urls = await _discover_swagger_urls_with_fallback(services)
                        
                        if swagger_urls:
                            logger.info(f"Swagger URL 발견: {swagger_urls}")
                            return swagger_urls
                    else:
                        logger.warning(f"Pod에 대응하는 서비스를 찾을 수 없음: {pod_name}")
                        
            except Exception as e:
                logger.error(f"Pod 정보 조회 오류: {pod_name}, error: {str(e)}")
                continue
        
        logger.warning(f"SERVER 타입 Pod을 찾을 수 없음: {service_name}")
        return []
        
    except Exception as e:
        logger.error(f"Swagger URL 스캔 오류: {service_name}, error: {str(e)}")
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
            node_ports = service.get("node_ports", [])
            port_mappings = service.get("port_mappings", {})
            await _try_nodeport_fallback(service_name, node_ports, port_mappings, swagger_paths, swagger_urls)
    
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
