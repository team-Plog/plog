import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Any, Dict
import threading
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.models.sqlite.database import SessionLocal
from app.models.sqlite.models import ServerInfraModel, OpenAPISpecModel
from k8s.pod_service import PodService
from app.services.infrastructure.server_infra_service import ServerInfraService
from k8s.service_service import ServiceService
from app.services.openapi.strategy_factory import analyze_openapi_with_strategy
from app.services.openapi.openapi_service import save_openapi_spec
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest

logger = logging.getLogger(__name__)


class ServerPodScheduler:
    """
    서버 Pod 상태를 모니터링하는 스케줄러

    1. Pod 상태 변화를 감지
    2. Pod 메트릭 수집
    3. 상태 정보를 데이터베이스에 저장
    """

    def __init__(self, poll_interval: int = None, max_retry_attempts: int = None):
        """
        Args:
            poll_interval: 폴링 간격(초) - None이면 설정에서 가져옴
            max_retry_attempts: 최대 재시도 횟수 - None이면 설정에서 가져옴
        """
        self.poll_interval = poll_interval or getattr(settings, 'POD_SCHEDULER_POLL_INTERVAL', 30)
        self.max_retry_attempts = max_retry_attempts or getattr(settings, 'POD_SCHEDULER_MAX_RETRY', 3)
        self.pod_timeout_hours = getattr(settings, 'POD_SCHEDULER_TIMEOUT_HOURS', 24)
        self.pod_warning_hours = getattr(settings, 'POD_SCHEDULER_WARNING_HOURS', 6)
        
        self.pod_service = PodService(namespace=settings.KUBERNETES_TEST_NAMESPACE)
        self.service_service = ServiceService(namespace=settings.KUBERNETES_TEST_NAMESPACE)
        self.server_infra_service = ServerInfraService()
        self.is_running = False
        self._scheduler_thread = None
        self._stop_event = threading.Event()
        
        # 재시도 중인 pod 추적
        self.retry_count = {}
        
        logger.info(f"Server Pod Scheduler initialized with poll_interval={self.poll_interval}s, max_retry={self.max_retry_attempts}")

    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("Server Pod Scheduler is already running")
            return
            
        self.is_running = True
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        logger.info(f"Server Pod Scheduler started with {self.poll_interval}s interval")

    def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            return
            
        self.is_running = False
        self._stop_event.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=10)
            
        logger.info("Server Pod Scheduler stopped")

    def _run_scheduler(self):
        """스케줄러 메인 루프"""
        logger.info("Server Pod Scheduler main loop started")
        
        # asyncio 이벤트 루프 설정
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.is_running and not self._stop_event.is_set():
            try:
                loop.run_until_complete(self._process_pod_status())
                
                # 다음 실행까지 대기
                self._stop_event.wait(timeout=self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in server pod scheduler main loop: {e}")
                # 에러 발생 시 짧은 대기 후 재시도
                self._stop_event.wait(timeout=5)
        
        loop.close()

    async def _process_pod_status(self):
        """Pod 상태를 처리"""
        db = SessionLocal()
        try:
            logger.info("✅ Starting pod status processing")
            # Get existing services and pods
            saved_services = self.server_infra_service.get_server_infra_group_names_with_openapi_spec_id(db)
            saved_service_map = {group_name: spec_id for spec_id, group_name in saved_services}
            existing_group_names = self.server_infra_service.get_server_infra_exists_group_names(db)
            existing_services_set = set(existing_group_names)

            scan_service_map = self.service_service.get_pods_for_all_services()

            new_server_infras = []
            delete_server_infra_names = []

            for service_name, pod_names in scan_service_map.items():
                if service_name in existing_services_set:
                    # Existing service: sync pods
                    spec_id = saved_service_map.get(service_name)
                    service_saved_pod_names = self.server_infra_service.get_existing_pod_names_by_group(
                        db, service_name, settings.KUBERNETES_TEST_NAMESPACE
                    )

                    # Add new pods
                    for pod_name in pod_names:
                        if pod_name not in service_saved_pod_names:
                            detailed_pod_info = self.pod_service.get_pod_details_with_owner_info(pod_name)
                            
                            server_infra = ServerInfraModel(
                                openapi_spec_id=spec_id,  # OpenAPI spec이 있으면 ID, 없으면 None
                                resource_type=detailed_pod_info.get("resource_type"), # DEPLOYMENT, DAEMONSET, STATEFULSET
                                name=pod_name,
                                service_type=detailed_pod_info.get("service_type"), # SERVER, DATABASE
                                environment="K3S",
                                group_name=service_name,  # 서비스 이름
                                label=detailed_pod_info.get("label"),
                                namespace=settings.KUBERNETES_TEST_NAMESPACE,
                            )
                            new_server_infras.append(server_infra)

                    # Mark pods for deletion
                    for saved_pod_name in service_saved_pod_names:
                        if saved_pod_name not in pod_names:
                            delete_server_infra_names.append(saved_pod_name)

                # New service processing
                else:
                    logger.info(f"✅ New service detected: {service_name}")
                    saved_openapi_spec = None
                    
                    # Find SERVER pod for OpenAPI registration
                    for pod_name in pod_names:
                        detailed_pod_info = self.pod_service.get_pod_details_with_owner_info(pod_name)
                        
                        if detailed_pod_info.get("service_type") == "SERVER":
                            services = self.pod_service.find_services_for_pod(detailed_pod_info["labels"])
                            swagger_urls = await self._discover_swagger_urls_with_fallback(services)

                            if not swagger_urls:
                                continue

                            # OpenAPI 분석 요청 생성
                            openapi_request = OpenAPISpecRegisterRequest(
                                open_api_url=swagger_urls[0],
                                project_id=1  # 기본 프로젝트 ID 사용
                            )

                            # OpenAPI 분석 수행 (nodeport 변환 매핑 전달)
                            conversion_mappings = getattr(self, '_nodeport_conversions', {}) if hasattr(self, '_nodeport_conversions') else {}
                            analysis_result = await analyze_openapi_with_strategy(
                                openapi_request,
                                db=db,
                                convert_url=True,
                                conversion_mappings=conversion_mappings
                            )

                            if analysis_result:
                                logger.info(f"✅ OpenAPI spec analyzed for {pod_name}")
                                # URL 변환 로직은 이제 analyze_openapi_with_strategy 내부에서 처리
                                saved_openapi_spec = save_openapi_spec(db, analysis_result)
                                break

                    # Save all pods to ServerInfra
                    for pod_name in pod_names:
                        detailed_pod_info = self.pod_service.get_pod_details_with_owner_info(pod_name)
                        
                        server_infra = ServerInfraModel(
                            openapi_spec_id=saved_openapi_spec.id if saved_openapi_spec else None,
                            resource_type=detailed_pod_info.get("resource_type"),  # DEPLOYMENT, DAEMONSET, STATEFULSET
                            name=pod_name,
                            service_type=detailed_pod_info.get("service_type"),  # SERVER, DATABASE
                            environment="K3S",
                            group_name=service_name,  # 서비스 이름
                            label=detailed_pod_info.get("label"),
                            namespace=settings.KUBERNETES_TEST_NAMESPACE,
                        )
                        new_server_infras.append(server_infra)

            # Apply changes
            if new_server_infras:
                db.add_all(new_server_infras)
                logger.info(f"✅ Added {len(new_server_infras)} new pods")
            
            if delete_server_infra_names:
                deleted_count = db.query(ServerInfraModel).filter(
                    ServerInfraModel.name.in_(delete_server_infra_names)
                ).delete(synchronize_session=False)
                logger.info(f"✅ Deleted {deleted_count} obsolete pods")
            
            if new_server_infras or delete_server_infra_names:
                db.commit()
                logger.info("✅ Pod status processing completed")

        except Exception as e:
            logger.error(f"Error processing pod status: {e}")
            db.rollback()
        finally:
            db.close()

    async def _discover_swagger_urls_with_fallback(self, services: List[Dict[str, Any]]) -> List[str]:
        """
        서비스 정보를 기반으로 Swagger URL을 탐지하고, 실패 시 NodePort로 fallback 시도
        
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
                if self._is_http_port(port):
                    service_url = f"http://{service_name}.{settings.KUBERNETES_TEST_NAMESPACE}.svc.cluster.local:{port}"
                    urls_found = await self._check_swagger_endpoints(service_url, swagger_paths)
                    swagger_urls.extend(urls_found)
                    
                    if cluster_ip and cluster_ip != "None":
                        cluster_url = f"http://{cluster_ip}:{port}"
                        urls_found = await self._check_swagger_endpoints(cluster_url, swagger_paths)
                        swagger_urls.extend(urls_found)
            
            # NodePort fallback
            if service_type == "NodePort":
                node_ports = service.get("node_ports", [])
                port_mappings = service.get("port_mappings", {})
                await self._try_nodeport_fallback(service_name, node_ports, port_mappings, swagger_paths, swagger_urls)
        
        return swagger_urls

    async def _check_swagger_endpoints(self, base_url: str, swagger_paths: List[str]) -> List[str]:
        """
        주어진 base URL에 대해 swagger paths를 병렬로 확인하여 유효한 엔드포인트를 찾습니다.
        세마포어로 동시 연결 수 제한, 클라이언트 재사용, 조기 종료 최적화 적용
        """
        potential_urls = [f"{base_url}{swagger_path}" for swagger_path in swagger_paths]
        semaphore = asyncio.Semaphore(5)
        
        async def check_single_url_with_semaphore(client, url):
            async with semaphore:
                return await self._check_swagger_url_with_client(client, url)
        
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

    async def _try_nodeport_fallback(self, service_name: str, node_ports: List[int], 
                                   port_mappings: Dict[int, int], swagger_paths: List[str], swagger_urls: List[str]):
        """
        NodePort 서비스에 대해 localhost로 fallback 시도
        localhost URL을 그대로 반환 (OpenAPI 분석에 사용)
        """
        # node_ports 배열에는 이미 NodePort 포트만 들어있음
        for node_port in node_ports:
            localhost_url = f"http://localhost:{node_port}"
            urls_found = await self._check_swagger_endpoints(localhost_url, swagger_paths)
            
            if urls_found:
                swagger_urls.extend(urls_found)
                service_port = port_mappings.get(node_port, node_port)
                if not hasattr(self, '_nodeport_conversions'):
                    self._nodeport_conversions = {}
                
                for url in urls_found:
                    self._nodeport_conversions[url] = {
                        'service_name': service_name,
                        'service_port': service_port,
                        'node_port': node_port
                    }

    async def _check_swagger_url_with_client(self, client, url: str) -> bool:
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
    
    async def _check_swagger_url_async(self, url: str, timeout: int = 3) -> bool:
        """
        비동기적으로 주어진 URL이 유효한 Swagger 엔드포인트인지 확인합니다.
        (하위 호환성을 위한 래퍼 메소드)
        """
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            return await self._check_swagger_url_with_client(client, url)

    def _is_http_port(self, port: int) -> bool:
        """
        포트가 HTTP 서비스 포트인지 추정합니다.
        """
        common_http_ports = [80, 8080, 3000, 4000, 5000, 8000, 9000]
        return port in common_http_ports or (8000 <= port <= 9999)
    
    def _convert_nodeport_url_if_needed(self, analysis_result, swagger_url):
        """
        NodePort fallback URL인 경우 base_url을 service_name:port로 변환
        
        Args:
            analysis_result: OpenAPI 분석 결과
            swagger_url: 변환 확인할 Swagger URL
            
        Returns:
            변환된 analysis_result (변환이 필요하지 않으면 원본 반환)
        """
        if hasattr(self, '_nodeport_conversions') and swagger_url in self._nodeport_conversions:
            conversion_info = self._nodeport_conversions[swagger_url]
            original_base_url = analysis_result.base_url
            
            service_with_namespace = f"{conversion_info['service_name']}.{settings.KUBERNETES_TEST_NAMESPACE}.svc.cluster.local"
            converted_base_url = original_base_url.replace(
                f"localhost:{conversion_info['node_port']}",
                f"{service_with_namespace}:{conversion_info['service_port']}"
            )
            analysis_result.base_url = converted_base_url
            
        return analysis_result


# 전역 스케줄러 인스턴스
_scheduler_instance = None


def get_scheduler() -> ServerPodScheduler:
    """스케줄러 인스턴스 반환 (싱글톤)"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ServerPodScheduler()
    return _scheduler_instance


def start_scheduler():
    """스케줄러 시작"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """스케줄러 중지"""
    scheduler = get_scheduler()
    scheduler.stop()