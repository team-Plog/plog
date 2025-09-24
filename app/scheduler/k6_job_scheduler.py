import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Any, Dict
import threading
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sqlite.database import SessionLocal, AsyncSessionLocal
from app.models.sqlite.models import TestHistoryModel, ScenarioHistoryModel
from k8s.job_service import JobService
from app.services.monitoring.metrics_aggregation_service import MetricsAggregationService
from app.services.monitoring.influxdb_service import InfluxDBService
from k8s.resource_service import ResourceService
from app.services.testing.test_history_service import (
    get_test_history_by_job_name,
    get_scenario_histories_by_test_id,
    update_test_history_with_metrics,
    update_scenario_history_with_metrics,
    mark_test_as_completed,
    save_test_timeseries_metrics,
    save_test_resource_metrics,
    get_scenario_by_server_infra_id,
    get_group_pods_names_by_server_infra_id,
    get_test_history_by_id,
    mark_analysis_as_completed
)
from app.services.analysis.ai_analysis_service import AIAnalysisService
from app.schemas.analysis.analysis_request import AnalysisType

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
        
        self.job_service = JobService(namespace=settings.KUBERNETES_PLOG_NAMESPACE)
        self.metrics_service = MetricsAggregationService()
        self.influxdb_service = InfluxDBService()  # 새로운 InfluxDB 서비스
        self.resource_service = ResourceService(namespace=settings.KUBERNETES_TEST_NAMESPACE)
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
            completed_jobs = self.job_service.list_completed_jobs()
            
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
                save_success = save_test_timeseries_metrics(db, scenario_histories, timeseries_data)

                # 6. 서버 리소스 메트릭 수집 및 저장 (CPU, Memory)
                self._collect_and_save_resource_metrics(db, test_history)

                # 6. test history를 완료 상태로 마킹
                mark_test_as_completed(db, test_history)

                # 7. AI 분석 자동 실행
                self._trigger_ai_analysis(test_history.id)

                # 8. 완료된 job 정리 (설정에 따라)
                if self.auto_delete_jobs:
                    self.job_service.delete_completed_job(job_name)

                logger.info(f"Successfully processed completed job: {job_name}")

        except Exception as e:
            logger.error(f"Error processing completed jobs: {e}")
        finally:
            db.close()

    def _collect_and_save_resource_metrics(self, db: Session, test_history: TestHistoryModel):
        """
        서버 리소스 메트릭(CPU, Memory) 수집 및 저장
        
        Args:
            db: 데이터베이스 세션
            test_history: 테스트 히스토리 모델
        """
        try:
            # 수집 대상 server_infra 추적
            scenario_histories = test_history.scenarios
            scenario_history_ids = [sh.id for sh in scenario_histories]
            job_name = test_history.job_name

            if not scenario_histories:
                logger.warning(f"Empty scenario histories")
                return

            for scenario_history in scenario_histories:
                endpoint = scenario_history.endpoint
                openapi_spec_version = endpoint.openapi_spec_version
                openapi_spec = openapi_spec_version.openapi_spec
                server_infras = openapi_spec.server_infras

                if not server_infras:
                    logger.warning(f"No server infra found for scenario: {scenario_history.id}")

                time_range = self.influxdb_service.get_test_time_range(job_name)
                if not time_range:
                    logger.warning(f"No time range found for job: {job_name} - skipping resource metrics collection")
                    return

                # 시나리오별 resource metrics 조회
                start_time, end_time = time_range
                extended_start = start_time - timedelta(minutes=1)
                extended_end = end_time + timedelta(minutes=1)

                logger.info(f"Test time range: {start_time} ~ {end_time}")
                logger.info(f"Extended collection range: {extended_start} ~ {extended_end}")

                # server infra 정보 알고, 시나리오 루프 돌고 있으니 차례대로 저장
                for server_infra in server_infras:
                    pod_name = server_infra.name
                    
                    # Pod의 resource spec 조회
                    resource_specs = self.resource_service.get_pod_aggregated_resources(pod_name)
                    logger.info(f"debug k6 job scheduler resource_sepcs: {resource_specs}")
                    
                    # CPU 메트릭 수집 및 스마트 보정
                    cpu_metrics = self.influxdb_service.get_cpu_metrics(pod_name, extended_start, extended_end)
                    logger.info(f"debug k6 job scheduler cpu_metrics: {cpu_metrics}")
                    
                    # SmartMetricsBuffer를 사용한 빈 값 보정 적용
                    if cpu_metrics:
                        cpu_metrics = self.influxdb_service.apply_smart_interpolation(cpu_metrics, 'cpu', pod_name)
                        logger.info(f"Applied smart interpolation to CPU metrics for {pod_name}")
                    
                    if cpu_metrics and resource_specs:
                        # CPU 메트릭에 resource spec 정보 추가
                        for metric in cpu_metrics:
                            metric['cpu_request_millicores'] = resource_specs['cpu_request_millicores']
                            metric['cpu_limit_millicores'] = resource_specs['cpu_limit_millicores']
                            metric['memory_request_mb'] = resource_specs['memory_request_mb']
                            metric['memory_limit_mb'] = resource_specs['memory_limit_mb']
                    save_success = save_test_resource_metrics(db, scenario_history, server_infra.id, cpu_metrics)
                    logger.info(f"debug k6 job scheduler save_success: {save_success}")

                    # Memory 메트릭 수집 및 스마트 보정
                    memory_metrics = self.influxdb_service.get_memory_metrics(pod_name, extended_start, extended_end)
                    logger.info(f"debug k6 job scheduler memory_metrics: {memory_metrics}")
                    
                    # SmartMetricsBuffer를 사용한 빈 값 보정 적용
                    if memory_metrics:
                        memory_metrics = self.influxdb_service.apply_smart_interpolation(memory_metrics, 'memory', pod_name)
                        logger.info(f"Applied smart interpolation to Memory metrics for {pod_name}")
                    
                    if memory_metrics and resource_specs:
                        # Memory 메트릭에 resource spec 정보 추가
                        for metric in memory_metrics:
                            metric['cpu_request_millicores'] = resource_specs['cpu_request_millicores']
                            metric['cpu_limit_millicores'] = resource_specs['cpu_limit_millicores']
                            metric['memory_request_mb'] = resource_specs['memory_request_mb']
                            metric['memory_limit_mb'] = resource_specs['memory_limit_mb']
                    save_success = save_test_resource_metrics(db, scenario_history, server_infra.id, memory_metrics)
                    logger.info(f"debug k6 job scheduler save_success: {save_success}")

        except Exception as e:
            logger.error(f"Error collecting and saving resource metrics for test_history {test_history.id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _trigger_ai_analysis(self, test_history_id: int):
        """AI 분석 자동 실행 (별도 스레드에서 실행)"""
        try:
            # 별도 스레드에서 AI 분석 실행하여 스케줄러 블로킹 방지
            analysis_thread = threading.Thread(
                target=self._run_ai_analysis,
                args=(test_history_id,),
                daemon=True
            )
            analysis_thread.start()
            logger.info(f"Started AI analysis thread for test_history_id: {test_history_id}")

        except Exception as e:
            logger.error(f"Error triggering AI analysis for test_history_id {test_history_id}: {e}")

    def _run_ai_analysis(self, test_history_id: int):
        """통합 AI 분석 수행 (별도 스레드에서 실행)"""
        try:
            logger.info(f"Starting unified comprehensive AI analysis for test_history_id: {test_history_id}")

            # AI 분석 서비스 초기화
            ai_service = AIAnalysisService()

            # 동기/비동기 DB 세션 생성
            sync_db = SessionLocal()

            try:
                # 통합 분석 실행 (기존 5개 개별 분석을 1개로 통합)
                async def run_unified_analysis():
                    async_db = AsyncSessionLocal()
                    try:
                        # 통합 분석 메서드 사용
                        comprehensive_result = await ai_service.perform_comprehensive_analysis(
                            sync_db, async_db, test_history_id
                        )

                        logger.info(f"Unified comprehensive analysis completed for test_history_id: {test_history_id}")
                        logger.info(f"Analysis included {len(comprehensive_result.analyses)} individual analysis results")

                        # 각 분석 영역의 성능 점수 로깅
                        for analysis in comprehensive_result.analyses:
                            score_info = f" (score: {analysis.performance_score})" if analysis.performance_score else ""
                            logger.info(f"  - {analysis.analysis_type.value}: {analysis.summary[:50]}...{score_info}")

                        return comprehensive_result

                    except Exception as e:
                        logger.error(f"Comprehensive analysis failed for test_history_id {test_history_id}: {e}")
                        return None

                    finally:
                        await async_db.close()

                # 비동기 분석 실행
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                analysis_result = loop.run_until_complete(run_unified_analysis())

                # 분석 완료 후 상태 업데이트
                test_history = get_test_history_by_id(sync_db, test_history_id)
                if test_history:
                    mark_analysis_as_completed(sync_db, test_history)

                    if analysis_result:
                        logger.info(f"Unified AI analysis completed and marked for test_history_id: {test_history_id}")
                        logger.info(f"Overall performance score: {analysis_result.overall_performance_score}")
                    else:
                        logger.info(f"Fallback AI analysis completed and marked for test_history_id: {test_history_id}")
                else:
                    logger.error(f"Test history not found for id: {test_history_id}")

            finally:
                sync_db.close()

        except Exception as e:
            logger.error(f"Error in AI analysis for test_history_id {test_history_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")


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