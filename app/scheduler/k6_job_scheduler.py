import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Any, Dict
import threading
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.sqlite.database import SessionLocal
from app.db.sqlite.models import TestHistoryModel, ScenarioHistoryModel
from app.services.monitoring.job_monitor_service import JobMonitorService
from app.services.monitoring.metrics_aggregation_service import MetricsAggregationService
from app.services.monitoring.influxdb_service import InfluxDBService
from app.services.testing.test_history_service import (
    get_test_history_by_job_name,
    get_scenario_histories_by_test_id,
    update_test_history_with_metrics,
    update_scenario_history_with_metrics,
    mark_test_as_completed,
    save_test_timeseries_metrics
)

logger = logging.getLogger(__name__)


class K6JobScheduler:
    """
    k6 Job 완료를 모니터링하고 메트릭을 수집하는 스케줄러

    1. 완료된 JOB을 조회
    """

    def __init__(self, poll_interval: int = None, max_retry_attempts: int = None):
        """
        Args:server_infra
            poll_interval: 폴링 간격(초) - None이면 설정에서 가져옴
            max_retry_attempts: 최대 재시도 횟수 - None이면 설정에서 가져옴
        """
        self.poll_interval = poll_interval or settings.SCHEDULER_POLL_INTERVAL
        self.max_retry_attempts = max_retry_attempts or settings.SCHEDULER_MAX_RETRY
        self.metrics_delay = settings.SCHEDULER_METRICS_DELAY
        self.job_timeout_hours = settings.SCHEDULER_JOB_TIMEOUT_HOURS
        self.job_warning_hours = settings.SCHEDULER_JOB_WARNING_HOURS
        self.auto_delete_jobs = settings.AUTO_DELETE_COMPLETED_JOBS
        
        self.job_monitor = JobMonitorService(namespace=settings.KUBERNETES_PLOG_NAMESPACE)
        self.metrics_service = MetricsAggregationService()
        self.influxdb_service = InfluxDBService()  # 새로운 InfluxDB 서비스
        self.is_running = False
        self._scheduler_thread = None
        self._stop_event = threading.Event()
        
        # 재시도 중인 job 추적
        self.retry_count = {}
        
        logger.info(f"Scheduler initialized with poll_interval={self.poll_interval}s, max_retry={self.max_retry_attempts}")

    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        logger.info(f"K6 Job Scheduler started with {self.poll_interval}s interval")

    def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            return
            
        self.is_running = False
        self._stop_event.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=10)
            
        logger.info("K6 Job Scheduler stopped")

    def _run_scheduler(self):
        """스케줄러 메인 루프"""
        logger.info("Scheduler main loop started")
        
        while self.is_running and not self._stop_event.is_set():
            try:
                self._process_completed_jobs()
                
                # 다음 실행까지 대기
                self._stop_event.wait(timeout=self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in scheduler main loop: {e}")
                # 에러 발생 시 짧은 대기 후 재시도
                self._stop_event.wait(timeout=5)


    def _process_completed_jobs(self):
        """완료된 JOB을 처리"""
        db = SessionLocal()
        try:
            # 1. 완료된(성공, 실패) 작업 조회
            completed_jobs = self.job_monitor.list_completed_jobs()
            
            for job in completed_jobs:
                job_name = job['name']                    # 실제 Kubernetes Job 이름

                # 1. SQLite에서 job_name을 가지고 test_history, scenario_history를 조회
                test_history:TestHistoryModel = get_test_history_by_job_name(db, job_name)
                if not test_history:
                    logger.warning(f"No test history found for job: {job_name} - skipping processing")
                    continue
                    
                scenario_histories:List[ScenarioHistoryModel] = test_history.scenarios

                # 2. InfluxDB의 job_name과 매칭하여 테스트 전체 TPS, 응답시간, 에러율 계산
                overall_metrics:Dict[str, Any] = self.influxdb_service.get_overall_metrics(job_name=test_history.job_name)

                # 3. 조회한 test_history에 업데이트 (null 체크 추가)
                if overall_metrics:
                    update_test_history_with_metrics(db, test_history, overall_metrics)
                    logger.info(f"Updated overall metrics for job: {job_name}")
                else:
                    logger.warning(f"No overall metrics found for job: {job_name} - skipping update")

                # 4. scenario_history.scenario_tag를 통해 influxdb에서 시나리오별 메트릭 조회 및 업데이트
                for scenario_history in scenario_histories:
                    scenario_identifier = scenario_history.scenario_tag  # 테스트 시나리오 태그(쿼리할 때 사용하는 내부 식별자)
                    scenario_metrics = self.influxdb_service.get_scenario_metrics(scenario_identifier)
                    if scenario_metrics:
                        update_scenario_history_with_metrics(db, scenario_history, scenario_metrics)
                        logger.info(f"Updated scenario metrics for scenario: {scenario_identifier}")
                    else:
                        logger.warning(f"No scenario metrics found for scenario: {scenario_identifier} - skipping update")

                # 5. 시계열 메트릭 데이터 수집 및 저장
                timeseries_data = self.influxdb_service.get_test_timeseries_data(job_name)
                if timeseries_data:
                    save_success = save_test_timeseries_metrics(db, test_history.id, timeseries_data)
                    if save_success:
                        logger.info(f"Saved {len(timeseries_data)} timeseries data points for job: {job_name}")
                    else:
                        logger.error(f"Failed to save timeseries data for job: {job_name}")
                else:
                    logger.warning(f"No timeseries data found for job: {job_name} - skipping timeseries save")

                # 6. test history를 완료 상태로 마킹
                mark_test_as_completed(db, test_history)
                
                # 6. 완료된 job 정리 (설정에 따라)
                if self.auto_delete_jobs:
                    self.job_monitor.delete_completed_job(job_name)
                    
                logger.info(f"Successfully processed completed job: {job_name}")

        except Exception as e:
            logger.error(f"Error processing completed jobs: {e}")
        finally:
            db.close()


# 전역 스케줄러 인스턴스
_scheduler_instance = None


def get_scheduler() -> K6JobScheduler:
    """스케줄러 인스턴스 반환 (싱글톤)"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = K6JobScheduler()
    return _scheduler_instance


def start_scheduler():
    """스케줄러 시작"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """스케줄러 중지"""
    scheduler = get_scheduler()
    scheduler.stop()