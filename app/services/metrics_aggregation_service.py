import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.db.influxdb.database import client

logger = logging.getLogger(__name__)


class MetricsAggregationService:
    """InfluxDB에서 k6 테스트 완료 후 최종 메트릭을 집계하는 서비스"""

    def __init__(self):
        self.influx_client = client

    def get_test_final_metrics(self, job_name: str, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
        """
        특정 job의 전체 테스트 기간 동안의 최종 메트릭을 조회합니다.
        
        Args:
            job_name: k6 Job 이름
            start_time: 테스트 시작 시간 (선택사항)
            end_time: 테스트 종료 시간 (선택사항)
            
        Returns:
            전체 테스트 결과 메트릭
        """
        try:
            logger.info(f"Aggregating final metrics for job: {job_name}")
            
            # 시간 범위 설정
            time_filter = self._build_time_filter(job_name, start_time, end_time)
            
            # 각 메트릭 조회
            overall_metrics = {
                'total_requests': self._get_total_requests(job_name, time_filter),
                'failed_requests': self._get_failed_requests(job_name, time_filter),
                'avg_response_time': self._get_avg_response_time(job_name, time_filter),
                'max_response_time': self._get_max_response_time(job_name, time_filter),
                'min_response_time': self._get_min_response_time(job_name, time_filter),
                'p95_response_time': self._get_p95_response_time(job_name, time_filter),
                'max_vus': self._get_max_vus(job_name, time_filter),
                'test_duration': self._get_test_duration(job_name, time_filter)
            }
            
            # TPS 계산
            if overall_metrics['total_requests'] and overall_metrics['test_duration']:
                overall_metrics['actual_tps'] = overall_metrics['total_requests'] / overall_metrics['test_duration']
            else:
                overall_metrics['actual_tps'] = 0.0
            
            # 에러율 계산
            if overall_metrics['total_requests'] and overall_metrics['total_requests'] > 0:
                overall_metrics['error_rate'] = (overall_metrics['failed_requests'] / overall_metrics['total_requests']) * 100
            else:
                overall_metrics['error_rate'] = 0.0
            
            logger.info(f"Final metrics aggregated for {job_name}: TPS={overall_metrics['actual_tps']:.2f}, Error Rate={overall_metrics['error_rate']:.2f}%")
            return overall_metrics
            
        except Exception as e:
            logger.error(f"Error aggregating metrics for job {job_name}: {e}")
            return self._get_default_metrics()

    def get_scenario_final_metrics(self, job_name: str, scenario_name: str, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
        """
        특정 시나리오의 최종 메트릭을 조회합니다.
        
        Args:
            job_name: k6 Job 이름
            scenario_name: 시나리오 이름
            start_time: 테스트 시작 시간 (선택사항)
            end_time: 테스트 종료 시간 (선택사항)
            
        Returns:
            시나리오별 테스트 결과 메트릭
        """
        try:
            logger.info(f"Aggregating scenario metrics for job: {job_name}, scenario: {scenario_name}")
            
            # 시간 범위 설정 (시나리오 필터 추가)
            time_filter = self._build_time_filter(job_name, start_time, end_time, scenario_name)
            
            scenario_metrics = {
                'total_requests': self._get_total_requests(job_name, time_filter),
                'failed_requests': self._get_failed_requests(job_name, time_filter),
                'avg_response_time': self._get_avg_response_time(job_name, time_filter),
                'max_response_time': self._get_max_response_time(job_name, time_filter),
                'min_response_time': self._get_min_response_time(job_name, time_filter),
                'p95_response_time': self._get_p95_response_time(job_name, time_filter),
                'test_duration': self._get_test_duration(job_name, time_filter)
            }
            
            # TPS 계산
            if scenario_metrics['total_requests'] and scenario_metrics['test_duration']:
                scenario_metrics['actual_tps'] = scenario_metrics['total_requests'] / scenario_metrics['test_duration']
            else:
                scenario_metrics['actual_tps'] = 0.0
            
            # 에러율 계산
            if scenario_metrics['total_requests'] and scenario_metrics['total_requests'] > 0:
                scenario_metrics['error_rate'] = (scenario_metrics['failed_requests'] / scenario_metrics['total_requests']) * 100
            else:
                scenario_metrics['error_rate'] = 0.0
            
            return scenario_metrics
            
        except Exception as e:
            logger.error(f"Error aggregating scenario metrics for job {job_name}, scenario {scenario_name}: {e}")
            return self._get_default_metrics()

    def get_all_scenarios_for_job(self, job_name: str) -> List[str]:
        """Job에 속한 모든 시나리오 이름을 조회합니다."""
        try:
            query = f'''
                SHOW TAG VALUES FROM "http_reqs" 
                WITH KEY = "scenario" 
                WHERE "job_name" = '{job_name}'
            '''
            result = self.influx_client.query(query)
            
            scenarios = []
            for point in result.get_points():
                if 'value' in point:
                    scenarios.append(point['value'])
            
            logger.info(f"Found {len(scenarios)} scenarios for job {job_name}: {scenarios}")
            return scenarios
            
        except Exception as e:
            logger.error(f"Error getting scenarios for job {job_name}: {e}")
            return []

    def _build_time_filter(self, job_name: str, start_time: datetime = None, end_time: datetime = None, scenario_name: str = None) -> str:
        """InfluxDB 쿼리용 시간 필터를 생성합니다."""
        conditions = [f'"job_name" = \'{job_name}\'']
        
        if scenario_name:
            conditions.append(f'"scenario" = \'{scenario_name}\'')
        
        if start_time:
            conditions.append(f"time >= '{start_time.isoformat()}Z'")
        
        if end_time:
            conditions.append(f"time <= '{end_time.isoformat()}Z'")
        
        return " AND ".join(conditions)

    def _get_total_requests(self, job_name: str, time_filter: str) -> int:
        """총 요청 수를 조회합니다."""
        try:
            query = f'''
                SELECT COUNT("value") as total
                FROM "http_reqs"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return points[0]['total'] if points else 0
        except Exception as e:
            logger.error(f"Error getting total requests: {e}")
            return 0

    def _get_failed_requests(self, job_name: str, time_filter: str) -> int:
        """실패한 요청 수를 조회합니다."""
        try:
            query = f'''
                SELECT COUNT("value") as failed
                FROM "http_reqs"
                WHERE {time_filter} AND "status" >= '400'
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return points[0]['failed'] if points else 0
        except Exception as e:
            logger.error(f"Error getting failed requests: {e}")
            return 0

    def _get_avg_response_time(self, job_name: str, time_filter: str) -> float:
        """평균 응답 시간을 조회합니다."""
        try:
            query = f'''
                SELECT MEAN("value") as avg_time
                FROM "http_req_duration"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return round(points[0]['avg_time'], 2) if points and points[0]['avg_time'] else 0.0
        except Exception as e:
            logger.error(f"Error getting avg response time: {e}")
            return 0.0

    def _get_max_response_time(self, job_name: str, time_filter: str) -> float:
        """최대 응답 시간을 조회합니다."""
        try:
            query = f'''
                SELECT MAX("value") as max_time
                FROM "http_req_duration"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return round(points[0]['max_time'], 2) if points and points[0]['max_time'] else 0.0
        except Exception as e:
            logger.error(f"Error getting max response time: {e}")
            return 0.0

    def _get_min_response_time(self, job_name: str, time_filter: str) -> float:
        """최소 응답 시간을 조회합니다."""
        try:
            query = f'''
                SELECT MIN("value") as min_time
                FROM "http_req_duration"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return round(points[0]['min_time'], 2) if points and points[0]['min_time'] else 0.0
        except Exception as e:
            logger.error(f"Error getting min response time: {e}")
            return 0.0

    def _get_p95_response_time(self, job_name: str, time_filter: str) -> float:
        """95퍼센타일 응답 시간을 조회합니다."""
        try:
            query = f'''
                SELECT PERCENTILE("value", 95) as p95_time
                FROM "http_req_duration"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return round(points[0]['p95_time'], 2) if points and points[0]['p95_time'] else 0.0
        except Exception as e:
            logger.error(f"Error getting p95 response time: {e}")
            return 0.0

    def _get_max_vus(self, job_name: str, time_filter: str) -> int:
        """최대 Virtual Users 수를 조회합니다."""
        try:
            query = f'''
                SELECT MAX("value") as max_vus
                FROM "vus"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            return int(points[0]['max_vus']) if points and points[0]['max_vus'] else 0
        except Exception as e:
            logger.error(f"Error getting max VUs: {e}")
            return 0

    def _get_test_duration(self, job_name: str, time_filter: str) -> float:
        """테스트 실행 시간을 초 단위로 조회합니다."""
        try:
            query = f'''
                SELECT MIN(time) as start_time, MAX(time) as end_time
                FROM "http_reqs"
                WHERE {time_filter}
            '''
            result = self.influx_client.query(query)
            points = list(result.get_points())
            
            if points and points[0]['start_time'] and points[0]['end_time']:
                start = datetime.fromisoformat(points[0]['start_time'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(points[0]['end_time'].replace('Z', '+00:00'))
                duration = (end - start).total_seconds()
                return max(duration, 1.0)  # 최소 1초
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Error getting test duration: {e}")
            return 1.0

    def _get_default_metrics(self) -> Dict[str, Any]:
        """기본 메트릭 값을 반환합니다."""
        return {
            'total_requests': 0,
            'failed_requests': 0,
            'actual_tps': 0.0,
            'avg_response_time': 0.0,
            'max_response_time': 0.0,
            'min_response_time': 0.0,
            'p95_response_time': 0.0,
            'error_rate': 0.0,
            'max_vus': 0,
            'test_duration': 1.0
        }