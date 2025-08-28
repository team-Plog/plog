import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Any, Dict
import threading
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.db.sqlite.database import SessionLocal
from app.services.monitoring.pod_monitor_service import PodMonitorService
from app.services.infrastructure.server_infra_service import ServerInfraService
from app.services.openapi.strategy_factory import analyze_openapi_with_strategy
from app.services.openapi.service import save_openapi_spec
from app.dto.open_api_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest

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
        
        self.pod_monitor = PodMonitorService(namespace=getattr(settings, 'KUBERNETES_NAMESPACE', 'test'))
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
            # 1. test namespace에 실행 중인 POD를 스캔
            running_pods = self.pod_monitor.get_running_pods()
            logger.info(f"Found {len(running_pods)} running pods in test namespace")
            
            # 2. server_infra 테이블에 저장되어 있는 정보와 비교
            existing_pod_names = self.server_infra_service.get_existing_pod_names(db, "test")
            
            for pod_info in running_pods:
                pod_name = pod_info['name']
                
                # 아직 저장되어 있지 않은 POD들에 대해서만 처리
                if pod_name not in existing_pod_names:
                    logger.info(f"Processing new pod: {pod_name}")
                    
                    # 3. pod의 상세정보 중 ownerReferences를 타고 ReplicaSet -> Deployment까지 진행
                    detailed_pod_info = self.pod_monitor.get_pod_details_with_owner_info(pod_name)
                    
                    if detailed_pod_info:
                        # SERVER 타입 POD에 대해서만 서비스 발견 및 OpenAPI 분석 수행
                        if detailed_pod_info.get("service_type") == "SERVER":
                            await self._process_server_pod(db, detailed_pod_info)
                        else:
                            # DATABASE 타입은 기존대로 저장만
                            server_infra = self.server_infra_service.create_server_infra(
                                db=db,
                                pod_info=detailed_pod_info,
                                open_api_spec_id=None
                            )
                            
                            if server_infra:
                                logger.info(f"Successfully saved database pod {pod_name} to server_infra table")
                            else:
                                logger.error(f"Failed to save database pod {pod_name} to server_infra table")
                    else:
                        logger.error(f"Failed to get detailed info for pod {pod_name}")
                else:
                    logger.debug(f"Pod {pod_name} already exists in server_infra table")

        except Exception as e:
            logger.error(f"Error processing pod status: {e}")
        finally:
            db.close()

    async def _process_server_pod(self, db: Session, pod_info: Dict[str, Any]):
        """
        SERVER 타입 POD에 대해 서비스 발견과 OpenAPI 분석을 수행합니다.
        조건을 만족하지 않으면 Pod 정보를 저장하지 않아서 다음 스캔에서 재시도하도록 합니다.
        
        Args:
            db: 데이터베이스 세션
            pod_info: Pod 상세 정보
        """
        pod_name = pod_info.get("name")
        pod_labels = pod_info.get("labels", {})
        
        try:
            # 1. Pod의 라벨을 기반으로 연결된 Service 찾기
            logger.info(f"Finding services for pod {pod_name} with labels: {pod_labels}")
            services = self.pod_monitor.find_services_for_pod(pod_labels)
            
            if not services:
                logger.warning(f"No services found for pod {pod_name} - skipping save for retry")
                return  # 서비스가 없으면 저장하지 않음 (배포 중일 가능성)
            
            logger.info(f"Found {len(services)} services for pod {pod_name}: {[s['name'] for s in services]}")
            
            # 2. 서비스를 기반으로 Swagger URL 탐지 (클러스터 내부 IP 사용)
            swagger_urls = await self._discover_swagger_urls_with_fallback(services)
            
            if not swagger_urls:
                logger.warning(f"No Swagger URLs found for pod {pod_name} - skipping save for retry")
                return  # Swagger URL이 없으면 저장하지 않음 (애플리케이션 시작 중일 가능성)
            
            # 3. 첫 번째로 발견된 Swagger URL로 OpenAPI 분석 수행
            swagger_url = swagger_urls[0]
            logger.info(f"Analyzing OpenAPI spec from URL: {swagger_url}")
            
            try:
                # OpenAPI 분석 요청 생성
                openapi_request = OpenAPISpecRegisterRequest(
                    open_api_url=swagger_url,
                    project_id=1  # 기본 프로젝트 ID 사용
                )
                
                # OpenAPI 분석 수행
                analysis_result = await analyze_openapi_with_strategy(openapi_request)
                
                if analysis_result:
                    logger.info(f"Successfully analyzed OpenAPI spec for pod {pod_name}")
                    
                    # OpenAPI 분석 결과를 데이터베이스에 저장
                    saved_openapi_spec = await save_openapi_spec(db, analysis_result)
                    logger.info(f"Saved OpenAPI spec with ID: {saved_openapi_spec.id}")
                    
                    # server_infra 테이블에 저장 (OpenAPI spec과 연결)
                    server_infra = self.server_infra_service.create_server_infra(
                        db=db,
                        pod_info=pod_info,
                        open_api_spec_id=saved_openapi_spec.id  # 저장된 OpenAPI spec ID 사용
                    )
                    
                    if server_infra:
                        logger.info(f"Successfully saved server pod {pod_name} with OpenAPI spec connection")
                    else:
                        logger.error(f"Failed to save server pod {pod_name} - database error")
                else:
                    logger.warning(f"OpenAPI analysis returned no result for {swagger_url} - skipping save for retry")
                    return  # OpenAPI 분석 실패하면 저장하지 않음 (API 준비 중일 가능성)
                    
            except Exception as openapi_error:
                logger.error(f"Failed to analyze OpenAPI spec from {swagger_url}: {openapi_error} - skipping save for retry")
                return  # OpenAPI 분석 실패하면 저장하지 않음 (API 준비 중일 가능성)
                
        except Exception as e:
            logger.error(f"Error processing server pod {pod_name}: {e} - skipping save for retry")
            return  # 전체 처리 실패하면 저장하지 않음

    async def _discover_swagger_urls_with_fallback(self, services: List[Dict[str, Any]]) -> List[str]:
        """
        서비스 정보를 기반으로 Swagger URL을 탐지하고, 실패 시 NodePort로 fallback 시도
        
        Args:
            services: Service 정보 리스트
            
        Returns:
            발견된 Swagger URL 리스트
        """
        swagger_urls = []
        
        # 일반적인 Swagger 엔드포인트 패턴들 (성공 확률이 높은 순서로 정렬)
        swagger_paths = [
            "/v3/api-docs",         # Spring Boot 기본 경로 (가장 높은 성공률)
            "/swagger-ui",          # 일반적인 Swagger UI
            "/swagger-ui/index.html", # Swagger UI 인덱스 페이지
            "/api/swagger",         # API 네임스페이스 하위
            "/swagger",             # 간단한 swagger 경로
            "/docs",                # 문서 경로
            "/api/docs",            # API 문서 경로
            "/openapi.json",        # OpenAPI JSON 스펙
            "/swagger.json",        # Swagger JSON 스펙
            "/v1/api-docs",         # 버전별 API 문서
            "/v2/api-docs",         # 버전별 API 문서
            "/api-docs"             # API 문서
        ]
        
        for service in services:
            service_name = service["name"]
            cluster_ip = service["cluster_ip"]
            ports = service["ports"]
            service_type = service.get("type", "ClusterIP")
            
            # 1. 클러스터 내부 Service URL로 시도
            for port in ports:
                if self._is_http_port(port):
                    # http://<service_name>:port/~~ 형태로 시도
                    service_url = f"http://{service_name}:{port}"
                    urls_found = await self._check_swagger_endpoints(service_url, swagger_paths)
                    swagger_urls.extend(urls_found)
                    
                    # cluster IP로도 시도
                    if cluster_ip and cluster_ip != "None":
                        cluster_url = f"http://{cluster_ip}:{port}"
                        urls_found = await self._check_swagger_endpoints(cluster_url, swagger_paths)
                        swagger_urls.extend(urls_found)
            
            # 2. fallback: NodePort 타입인 경우 localhost로 시도
            if service_type == "NodePort":
                node_ports = service.get("node_ports", [])
                await self._try_nodeport_fallback(service_name, node_ports, swagger_paths, swagger_urls)
        
        return swagger_urls

    async def _check_swagger_endpoints(self, base_url: str, swagger_paths: List[str]) -> List[str]:
        """
        주어진 base URL에 대해 swagger paths를 병렬로 확인하여 유효한 엔드포인트를 찾습니다.
        세마포어로 동시 연결 수 제한, 클라이언트 재사용, 조기 종료 최적화 적용
        """
        potential_urls = [f"{base_url}{swagger_path}" for swagger_path in swagger_paths]
        logger.info(f"Checking {len(potential_urls)} URLs in parallel for {base_url}")
        
        # 세마포어로 최대 5개 동시 요청 제한
        semaphore = asyncio.Semaphore(5)
        
        async def check_single_url_with_semaphore(client, url):
            async with semaphore:
                return await self._check_swagger_url_with_client(client, url)
        
        # 클라이언트 재사용으로 모든 요청 처리 (리다이렉트 자동 따르기)
        async with httpx.AsyncClient(timeout=3, follow_redirects=True) as client:
            # 모든 URL 체크 작업 생성 (URL과 함께 쌍으로 저장)
            tasks = [(asyncio.create_task(check_single_url_with_semaphore(client, url)), url) 
                    for url in potential_urls]
            
            # 병렬로 모든 작업 실행하고 결과 수집
            try:
                task_list = [task for task, _ in tasks]
                results = await asyncio.gather(*task_list, return_exceptions=True)
                
                # 결과 확인하여 첫 번째 성공한 URL 찾기
                for i, (result, (_, url)) in enumerate(zip(results, tasks)):
                    logger.info(f"Result for {url}: {result} (type: {type(result)})")
                    
                    if result is True:
                        logger.info(f"Found Swagger URL: {url}")
                        return [url]
                    elif isinstance(result, Exception):
                        logger.debug(f"Error checking URL {url}: {result}")
                        
            except Exception as e:
                logger.error(f"Error in parallel URL checking: {e}")
                raise
            
            return []

    async def _try_nodeport_fallback(self, service_name: str, node_ports: List[int], 
                                   swagger_paths: List[str], swagger_urls: List[str]):
        """
        NodePort 서비스에 대해 localhost로 fallback 시도
        """
        # node_ports 배열에는 이미 NodePort 포트만 들어있음
        for port in node_ports:
            localhost_url = f"http://localhost:{port}"
            urls_found = await self._check_swagger_endpoints(localhost_url, swagger_paths)
            swagger_urls.extend(urls_found)
            
            if urls_found:
                logger.info(f"Found Swagger URL via NodePort fallback: {urls_found[0]}")

    async def _check_swagger_url_with_client(self, client, url: str) -> bool:
        """
        주어진 클라이언트를 사용하여 URL이 유효한 Swagger 엔드포인트인지 확인합니다.
        """
        try:
            response = await client.get(url)
            logger.info(f"Response for {url}: status={response.status_code}, content-type={response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                content = response.text
                logger.info(f"Response content preview for {url}: {content[:200]}...")
                
                content_lower = content.lower()
                # Swagger 관련 키워드들이 포함되어 있는지 확인
                swagger_keywords = [
                    "swagger", "openapi", "api documentation", 
                    "swagger-ui", "redoc", "rapidoc"
                ]
                
                keyword_found = any(keyword in content_lower for keyword in swagger_keywords)
                logger.info(f"Keyword check for {url}: found={keyword_found}")
                
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
                    logger.info(f"JSON check for {url}: is_dict={isinstance(json_data, dict)}, has_swagger_keys={json_check}")
                    
                    if json_check:
                        return True
                except Exception as json_error:
                    logger.info(f"JSON parse failed for {url}: {json_error}")
                    
        except Exception as e:
            logger.debug(f"Failed to check Swagger URL {url}: {e}")
            
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
        # 일반적인 HTTP 포트들
        common_http_ports = [80, 8080, 3000, 4000, 5000, 8000, 9000]
        
        # 8000-9999 범위의 포트들도 HTTP일 가능성이 높음
        return port in common_http_ports or (8000 <= port <= 9999)


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