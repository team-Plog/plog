import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
import threading
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.sqlite.database import SessionLocal
from app.services.job_monitor_service import JobMonitorService, JobStatus
from app.services.metrics_aggregation_service import MetricsAggregationService
from app.services.test_history_service import (
    get_incomplete_test_histories,
    update_test_history_final_metrics,
    get_test_history_by_job_name
)

logger = logging.getLogger(__name__)


class K6JobScheduler:
    """k6 Job 완료를 모니터링하고 메트릭을 수집하는 스케줄러"""

    def __init__(self, poll_interval: int = None, max_retry_attempts: int = None):
        """
        Args:
            poll_interval: 폴링 간격(초) - None이면 설정에서 가져옴
            max_retry_attempts: 최대 재시도 횟수 - None이면 설정에서 가져옴
        """
        self.poll_interval = poll_interval or settings.SCHEDULER_POLL_INTERVAL
        self.max_retry_attempts = max_retry_attempts or settings.SCHEDULER_MAX_RETRY
        self.metrics_delay = settings.SCHEDULER_METRICS_DELAY
        self.job_timeout_hours = settings.SCHEDULER_JOB_TIMEOUT_HOURS
        self.job_warning_hours = settings.SCHEDULER_JOB_WARNING_HOURS
        self.auto_delete_jobs = settings.AUTO_DELETE_COMPLETED_JOBS
        
        self.job_monitor = JobMonitorService(namespace=settings.KUBERNETES_NAMESPACE)
        self.metrics_service = MetricsAggregationService()
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
                self._process_incomplete_jobs()
                
                # 다음 실행까지 대기
                self._stop_event.wait(timeout=self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in scheduler main loop: {e}")
                # 에러 발생 시 짧은 대기 후 재시도
                self._stop_event.wait(timeout=5)

    def _process_incomplete_jobs(self):
        """완료되지 않은 Job들과 최근 완료된 Job들을 처리"""
        db = SessionLocal()
        try:
            # 완료되지 않은 테스트 히스토리 조회
            incomplete_tests = get_incomplete_test_histories(db)
            
            # 최근 완료되었지만 메트릭이 아직 수집되지 않은 Job들도 확인
            # (완료 상태이지만 actual_tps가 None인 경우 = 메트릭 미수집)
            recently_completed_tests = self._get_recently_completed_without_metrics(db)
            
            all_tests_to_process = incomplete_tests + recently_completed_tests
            
            if not all_tests_to_process:
                logger.debug("No jobs to process")
                return
                
            logger.info(f"Processing {len(incomplete_tests)} incomplete jobs and {len(recently_completed_tests)} recently completed jobs")
            
            for test_history in all_tests_to_process:
                if not test_history.job_name:
                    continue
                    
                try:
                    self._process_single_job(db, test_history.job_name)
                except Exception as e:
                    logger.error(f"Error processing job {test_history.job_name}: {e}")
                    
        finally:
            db.close()

    def _get_recently_completed_without_metrics(self, db: Session):
        """최근 완료되었지만 메트릭이 수집되지 않은 테스트들을 조회"""
        from datetime import datetime, timedelta
        
        # 지난 10분 내에 완료되었지만 actual_tps가 None인 테스트들
        recent_threshold = datetime.utcnow() - timedelta(minutes=10)
        
        return (
            db.query(TestHistoryModel)
            .filter(
                TestHistoryModel.is_completed == True,
                TestHistoryModel.completed_at.isnot(None),
                TestHistoryModel.completed_at >= recent_threshold,
                TestHistoryModel.actual_tps.is_(None)  # 메트릭이 아직 수집되지 않음
            )
            .order_by(TestHistoryModel.completed_at.desc())
            .all()
        )

    def _process_single_job(self, db: Session, job_name: str):
        """단일 Job 처리"""
        logger.debug(f"Checking job status: {job_name}")
        
        # Job 상태 확인
        job_info = self.job_monitor.get_job_status(job_name)
        job_status = job_info.get('status')
        
        if job_status == JobStatus.SUCCEEDED:
            logger.info(f"Job {job_name} completed successfully, collecting metrics")
            self._collect_and_save_metrics(db, job_name, job_info)
            
        elif job_status == JobStatus.FAILED:
            logger.warning(f"Job {job_name} failed")
            self._handle_failed_job(db, job_name)
            
        elif job_status == JobStatus.RUNNING:
            logger.debug(f"Job {job_name} is still running")
            # 실행 시간이 너무 길면 경고
            self._check_long_running_job(db, job_name)
            
        elif job_status == JobStatus.UNKNOWN:
            logger.warning(f"Job {job_name} status unknown, checking if metrics exist in InfluxDB")
            # Job이 사라졌을 수도 있으니 InfluxDB에서 메트릭이 있는지 확인
            if self._has_metrics_in_influxdb(job_name):
                logger.info(f"Found metrics for {job_name} in InfluxDB, proceeding with collection")
                self._collect_and_save_metrics(db, job_name, {'status': JobStatus.SUCCEEDED})
            else:
                self._handle_unknown_job(db, job_name)

    def _collect_and_save_metrics(self, db: Session, job_name: str, job_info: dict):
        """메트릭 수집 및 저장"""
        try:
            # Job 완료 시간으로부터 약간의 지연 후 메트릭 수집
            # (InfluxDB에 모든 데이터가 기록될 시간을 확보)
            completion_time = job_info.get('completion_time')
            if completion_time:
                # 설정된 지연 시간만큼 대기
                time_since_completion = datetime.now(completion_time.tzinfo) - completion_time
                if time_since_completion < timedelta(seconds=self.metrics_delay):
                    logger.info(f"Job {job_name} completed recently, waiting {self.metrics_delay}s for metrics to be fully written")
                    return
            
            # 전체 메트릭 수집
            overall_metrics = self.metrics_service.get_test_final_metrics(job_name)
            
            # 시나리오별 메트릭 수집
            scenarios = self.metrics_service.get_all_scenarios_for_job(job_name)
            scenario_metrics = {}
            
            for scenario_name in scenarios:
                scenario_metrics[scenario_name] = self.metrics_service.get_scenario_final_metrics(
                    job_name, scenario_name
                )
            
            # SQLite에 저장
            success = update_test_history_final_metrics(
                db, job_name, overall_metrics, scenario_metrics
            )
            
            if success:
                logger.info(f"Successfully saved final metrics for job: {job_name}")
                # 재시도 카운트 초기화
                self.retry_count.pop(job_name, None)
                
                # 완료된 Job 정리 (설정에 따라)
                if self.auto_delete_jobs:
                    self.job_monitor.delete_completed_job(job_name)
                
            else:
                logger.error(f"Failed to save metrics for job: {job_name}")
                self._increment_retry_count(job_name)
                
        except Exception as e:
            logger.error(f"Error collecting metrics for job {job_name}: {e}")
            self._increment_retry_count(job_name)

    def _handle_failed_job(self, db: Session, job_name: str):
        """실패한 Job 처리"""
        try:
            # 실패한 Job도 완료 상태로 마킹 (메트릭은 0으로 설정)
            default_metrics = {
                'total_requests': 0,
                'failed_requests': 0,
                'actual_tps': 0.0,
                'avg_response_time': 0.0,
                'max_response_time': 0.0,
                'min_response_time': 0.0,
                'p95_response_time': 0.0,
                'error_rate': 100.0,  # 실패한 경우 100% 에러율
                'max_vus': 0,
                'test_duration': 0.0
            }
            
            success = update_test_history_final_metrics(db, job_name, default_metrics)
            if success:
                logger.info(f"Marked failed job as completed: {job_name}")
                
        except Exception as e:
            logger.error(f"Error handling failed job {job_name}: {e}")

    def _handle_unknown_job(self, db: Session, job_name: str):
        """상태 불명 Job 처리"""
        retry_count = self.retry_count.get(job_name, 0)
        
        if retry_count >= self.max_retry_attempts:
            logger.warning(f"Job {job_name} exceeded max retry attempts, marking as failed")
            self._handle_failed_job(db, job_name)
        else:
            self._increment_retry_count(job_name)

    def _check_long_running_job(self, db: Session, job_name: str):
        """장시간 실행 중인 Job 확인"""
        try:
            test_history = get_test_history_by_job_name(db, job_name)
            if test_history and test_history.tested_at:
                runtime = datetime.utcnow() - test_history.tested_at
                
                # 설정된 경고 시간 이상 실행 중이면 경고
                warning_threshold = timedelta(hours=self.job_warning_hours)
                if runtime > warning_threshold:
                    logger.warning(f"Job {job_name} has been running for {runtime}")
                    
                # 설정된 타임아웃 시간 이상 실행 중이면 강제 종료 고려
                timeout_threshold = timedelta(hours=self.job_timeout_hours)
                if runtime > timeout_threshold:
                    logger.error(f"Job {job_name} has been running for {runtime}, consider manual intervention")
                    
        except Exception as e:
            logger.error(f"Error checking long running job {job_name}: {e}")

    def _has_metrics_in_influxdb(self, job_name: str) -> bool:
        """InfluxDB에 해당 job_name의 메트릭이 있는지 확인"""
        try:
            # 간단한 쿼리로 해당 job의 데이터가 있는지 확인
            result = self.metrics_service.influx_client.query(f'''
                SELECT COUNT("value") as count
                FROM "http_reqs"
                WHERE "job_name" = '{job_name}'
                LIMIT 1
            ''')
            
            points = list(result.get_points())
            has_data = points and points[0]['count'] > 0
            
            logger.debug(f"InfluxDB metrics check for {job_name}: {has_data}")
            return has_data
            
        except Exception as e:
            logger.error(f"Error checking InfluxDB metrics for {job_name}: {e}")
            return False

    def _increment_retry_count(self, job_name: str):
        """재시도 카운트 증가"""
        self.retry_count[job_name] = self.retry_count.get(job_name, 0) + 1
        logger.info(f"Retry count for job {job_name}: {self.retry_count[job_name]}/{self.max_retry_attempts}")

    def get_scheduler_status(self) -> dict:
        """스케줄러 상태 정보 반환"""
        return {
            'is_running': self.is_running,
            'poll_interval': self.poll_interval,
            'retry_jobs': dict(self.retry_count),
            'thread_alive': self._scheduler_thread.is_alive() if self._scheduler_thread else False
        }


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