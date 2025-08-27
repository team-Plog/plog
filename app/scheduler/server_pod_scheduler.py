import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Any, Dict
import threading
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.sqlite.database import SessionLocal
from app.services.monitoring.pod_monitor_service import PodMonitorService
from app.services.infrastructure.server_infra_service import ServerInfraService

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
        
        while self.is_running and not self._stop_event.is_set():
            try:
                self._process_pod_status()
                
                # 다음 실행까지 대기
                self._stop_event.wait(timeout=self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in server pod scheduler main loop: {e}")
                # 에러 발생 시 짧은 대기 후 재시도
                self._stop_event.wait(timeout=5)

    def _process_pod_status(self):
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
                        # server_infra 테이블에 저장
                        server_infra = self.server_infra_service.create_server_infra(
                            db=db,
                            pod_info=detailed_pod_info,
                            open_api_spec_id=None  # 아직 연결 안됨
                        )
                        
                        if server_infra:
                            logger.info(f"Successfully saved pod {pod_name} to server_infra table")
                        else:
                            logger.error(f"Failed to save pod {pod_name} to server_infra table")
                    else:
                        logger.error(f"Failed to get detailed info for pod {pod_name}")
                else:
                    logger.debug(f"Pod {pod_name} already exists in server_infra table")

        except Exception as e:
            logger.error(f"Error processing pod status: {e}")
        finally:
            db.close()


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