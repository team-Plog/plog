import logging
from typing import Dict, Optional, List, Tuple
from influxdb import InfluxDBClient
from app.core.config import settings
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


class InfluxDBService:
    """InfluxDB 메트릭 조회 서비스"""
    
    def __init__(self):
        self.client = InfluxDBClient(
            host=settings.INFLUXDB_HOST,
            port=settings.INFLUXDB_PORT,
            database=settings.INFLUXDB_DATABASE,
        )
    
    def get_overall_metrics(self, job_name: str) -> Optional[Dict]:
        """
        전체 테스트 메트릭 조회 - 모든 메트릭 통계 정보 포함
        
        Args:
            job_name: Kubernetes Job 이름
            
        Returns:
            전체 테스트 메트릭 딕셔너리 또는 None
            {
                'total_requests': int,           # 총 요청 수
                'failed_requests': int,          # 실패한 요청 수
                'actual_tps': float,             # 실제 계산된 TPS (total_requests/duration)
                'max_tps': float,                # 최대 TPS (5초 단위 집계)
                'min_tps': float,                # 최소 TPS (5초 단위 집계)
                'avg_tps': float,                # 평균 TPS (5초 단위 집계)
                'avg_response_time': float,      # 평균 응답 시간 (ms)
                'max_response_time': float,      # 최대 응답 시간 (ms)
                'min_response_time': float,      # 최소 응답 시간 (ms)
                'p50_response_time': float,      # 50번째 백분위수 응답 시간 (ms)
                'p95_response_time': float,      # 95번째 백분위수 응답 시간 (ms)
                'p99_response_time': float,      # 99번째 백분위수 응답 시간 (ms)
                'max_error_rate': float,         # 최대 에러율 (%)
                'min_error_rate': float,         # 최소 에러율 (%)
                'avg_error_rate': float,         # 평균 에러율 (%)
                'max_vus': int,                  # 최대 가상 사용자 수
                'min_vus': int,                  # 최소 가상 사용자 수
                'avg_vus': float,                # 평균 가상 사용자 수
                'test_duration': float           # 테스트 지속 시간 (seconds)
            }
        """
        try:
            # HTTP 요청 수 조회
            total_requests_query = f'''
                SELECT SUM("value") as total_requests
                FROM "http_reqs"
                WHERE "job_name" = '{job_name}'
            '''
            
            # 실패한 요청 수 조회  
            failed_requests_query = f'''
                SELECT SUM("value") as failed_requests
                FROM "http_reqs"
                WHERE "job_name" = '{job_name}' AND "status" !~ /^2../
            '''

            # min, max, avg tps 조회
            tps_query = f'''
                SELECT 
                    MAX(tps) as max_tps,
                    MIN(tps) as min_tps,
                    MEAN(tps) as avg_tps
                FROM (
                    SELECT SUM("value")/5 as tps
                    FROM "http_reqs"
                    WHERE "job_name" = '{job_name}'
                    GROUP BY time(5s) fill(none)
                )
            '''
            
            # 응답 시간 통계 조회
            response_time_query = f'''
                SELECT 
                    MEAN("value") as avg_response_time,
                    MAX("value") as max_response_time,
                    MIN("value") as min_response_time,
                    PERCENTILE("value", 50) as p50_response_time,
                    PERCENTILE("value", 95) as p95_response_time,
                    PERCENTILE("value", 99) as p99_response_time
                FROM "http_req_duration"
                WHERE "job_name" = '{job_name}'
            '''
            
            # VU (Virtual Users) 최대값 조회
            vus_query = f'''
                SELECT MAX("value") as max_vus, MIN("value") as min_vus, MEAN("value") as avg_vus
                FROM "vus"
                WHERE "job_name" = '{job_name}'
            '''

            # 에러율 통계 조회
            error_query = f'''
                SELECT MIN("err") AS min_err, MAX("err") AS max_err, MEAN("err") AS avg_err
                FROM (
                    SELECT MEAN("value") as err
                    FROM "http_req_failed"
                    WHERE "job_name" = '{job_name}'
                    GROUP BY time(5s) fill(none)
                )
            '''
            
            # 테스트 시작/종료 시간으로 duration 계산
            start_time_query = f'''
                SELECT * FROM "http_reqs"
                WHERE "job_name" = '{job_name}'
                ORDER BY time ASC LIMIT 1
            '''
            
            end_time_query = f'''
                SELECT * FROM "http_reqs"
                WHERE "job_name" = '{job_name}'
                ORDER BY time DESC LIMIT 1
            '''
            
            # 쿼리 실행
            total_result = list(self.client.query(total_requests_query).get_points())
            failed_result = list(self.client.query(failed_requests_query).get_points())
            tps_result = list(self.client.query(tps_query).get_points())
            response_result = list(self.client.query(response_time_query).get_points())
            error_result = list(self.client.query(error_query).get_points())
            vus_result = list(self.client.query(vus_query).get_points())
            start_time_result = list(self.client.query(start_time_query).get_points())
            end_time_result = list(self.client.query(end_time_query).get_points())
            
            if not total_result or not total_result[0]['total_requests']:
                logger.warning(f"No metrics found for job: {job_name}")
                return None
            
            # 결과 조합
            # 요청 수 조합
            total_requests = int(total_result[0]['total_requests'] or 0)
            failed_requests = int(failed_result[0]['failed_requests'] or 0) if failed_result else 0

            # TPS 조합
            max_tps = int(tps_result[0]['max_tps'] or 0)
            min_tps = int(tps_result[0]['min_tps'] or 0)
            avg_tps = int(tps_result[0]['avg_tps'] or 0)

            # 응답시간 조합
            response_data = response_result[0] if response_result else {}
            avg_response_time = float(response_data.get('avg_response_time', 0))
            max_response_time = float(response_data.get('max_response_time', 0))
            min_response_time = float(response_data.get('min_response_time', 0))
            p50_response_time = float(response_data.get('p50_response_time', 0))
            p95_response_time = float(response_data.get('p95_response_time', 0))
            p99_response_time = float(response_data.get('p99_response_time', 0))

            # 에러율 조합
            max_err = float(error_result[0]['max_err'] or 0)
            min_err = float(error_result[0]['min_err'] or 0)
            avg_err = float(error_result[0]['avg_err'] or 0)

            # 가상 사용자 수 조합
            max_vus = int(vus_result[0]['max_vus'] or 0) if vus_result else 0
            min_vus = int(vus_result[0]['min_vus'] or 0) if vus_result else 0
            avg_vus = int(vus_result[0]['avg_vus'] or 0) if vus_result else 0
            
            # Duration 계산 (초 단위)
            test_duration = 0.0
            if start_time_result and end_time_result:
                from datetime import datetime
                
                start_time_str = start_time_result[0]['time']
                end_time_str = end_time_result[0]['time']
                
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                test_duration = (end_time - start_time).total_seconds()
                
                # 디버깅 로그 추가
                logger.debug(f"Job {job_name} - Start: {start_time}, End: {end_time}, Duration: {test_duration}s")
            else:
                logger.warning(f"Job {job_name} - Could not get start/end times")
            
            # TPS 및 에러율 계산
            actual_tps = total_requests / test_duration if test_duration > 0 else 0.0
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
            
            # 디버깅 로그 추가
            logger.debug(f"Job {job_name} - Total Requests: {total_requests}, Duration: {test_duration}s, TPS: {actual_tps}")
            
            if actual_tps == 0.0:
                logger.warning(f"Job {job_name} - TPS is 0! Check: total_requests={total_requests}, test_duration={test_duration}")
            
            metrics = {
                'total_requests': total_requests,
                'failed_requests': failed_requests,

                'actual_tps': round(actual_tps, 2),  # TODO 평균 TPS 구할 때 actual vs avg
                'max_tps': max_tps,
                'min_tps': min_tps,
                'avg_tps': avg_tps,

                'avg_response_time': round(avg_response_time, 2),
                'max_response_time': round(max_response_time, 2),
                'min_response_time': round(min_response_time, 2),
                'p50_response_time': round(p50_response_time, 2),
                'p95_response_time': round(p95_response_time, 2),
                'p99_response_time': round(p99_response_time, 2),

                'max_error_rate': round(max_err, 2),
                'min_error_rate': round(min_err, 2),
                'avg_error_rate': round(avg_err, 2),

                'max_vus': max_vus,
                'min_vus': min_vus,
                'avg_vus': round(avg_vus, 2),

                'test_duration': round(test_duration, 2)
            }

            logger.info(f"Retrieved overall metrics for job {job_name}: TPS={actual_tps:.2f}, Error Rate={error_rate:.2f}%")
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving overall metrics for job {job_name}: {e}")
            return None
    
    def get_scenario_metrics(self, scenario_identifier: str) -> Optional[Dict]:
        """
        특정 시나리오(엔드포인트)의 메트릭 조회
        
        Args:
            scenario_identifier: 시나리오 식별자 (예: "job-name#endpoint-id")
            
        Returns:
            시나리오 메트릭 딕셔너리 또는 None
            {
                'total_requests': int,
                'failed_requests': int,
                'max_tps': float,
                'min_tps': float,
                'avg_tps': float,
                'avg_response_time': float,
                'max_response_time': float,
                'min_response_time': float,
                'p50_response_time': float,
                'p95_response_time': float,
                'p99_response_time': float,
                'max_error_rate': float,
                'min_error_rate': float,
                'avg_error_rate': float,
                'max_vus': int,
                'min_vus': int,
                'avg_vus': float,
                'test_duration': float
            }
        """
        try:
            # HTTP 요청 수 조회
            total_requests_query = f'''
                SELECT SUM("value") as total_requests
                FROM "http_reqs"
                WHERE "scenario" = '{scenario_identifier}'
            '''
            
            # 실패한 요청 수 조회
            failed_requests_query = f'''
                SELECT SUM("value") as failed_requests
                FROM "http_reqs"
                WHERE "scenario" = '{scenario_identifier}' AND "status" !~ /^2../
            '''

            # min, max, avg tps 조회
            tps_query = f'''
                SELECT 
                    MAX(tps) as max_tps,
                    MIN(tps) as min_tps,
                    MEAN(tps) as avg_tps
                FROM (
                    SELECT SUM("value")/5 as tps
                    FROM "http_reqs"
                    WHERE "scenario" = '{scenario_identifier}'
                    GROUP BY time(5s) fill(none)
                )
            '''
            
            # 응답 시간 통계 조회
            response_time_query = f'''
                SELECT 
                    MEAN("value") as avg_response_time,
                    MAX("value") as max_response_time,
                    MIN("value") as min_response_time,
                    PERCENTILE("value", 50) as p50_response_time,
                    PERCENTILE("value", 95) as p95_response_time,
                    PERCENTILE("value", 99) as p99_response_time
                FROM "http_req_duration"
                WHERE "scenario" = '{scenario_identifier}'
            '''

            # 에러율 통계 조회
            error_query = f'''
                SELECT MIN("err") AS min_err, MAX("err") AS max_err, MEAN("err") AS avg_err
                FROM (
                    SELECT MEAN("value") as err
                    FROM "http_req_failed"
                    WHERE "scenario" = '{scenario_identifier}'
                    GROUP BY time(5s) fill(none)
                )
            '''
            
            # 테스트 시간 조회 (duration 계산용)
            start_time_query = f'''
                SELECT * FROM "http_reqs"
                WHERE "scenario" = '{scenario_identifier}'
                ORDER BY time ASC LIMIT 1
            '''
            
            end_time_query = f'''
                SELECT * FROM "http_reqs"
                WHERE "scenario" = '{scenario_identifier}'
                ORDER BY time DESC LIMIT 1
            '''
            
            # 쿼리 실행
            total_result = list(self.client.query(total_requests_query).get_points())
            failed_result = list(self.client.query(failed_requests_query).get_points())
            tps_result = list(self.client.query(tps_query).get_points())
            response_result = list(self.client.query(response_time_query).get_points())
            error_result = list(self.client.query(error_query).get_points())
            start_time_result = list(self.client.query(start_time_query).get_points())
            end_time_result = list(self.client.query(end_time_query).get_points())
            
            if not total_result or not total_result[0]['total_requests']:
                logger.warning(f"No metrics found for scenario: {scenario_identifier}")
                return None
            
            # 결과 조합
            # 요청 수 조합
            total_requests = int(total_result[0]['total_requests'] or 0)
            failed_requests = int(failed_result[0]['failed_requests'] or 0) if failed_result else 0

            # TPS 조합
            max_tps = float(tps_result[0]['max_tps'] or 0) if tps_result else 0.0
            min_tps = float(tps_result[0]['min_tps'] or 0) if tps_result else 0.0
            avg_tps = float(tps_result[0]['avg_tps'] or 0) if tps_result else 0.0

            # 응답시간 조합
            response_data = response_result[0] if response_result else {}
            avg_response_time = float(response_data.get('avg_response_time', 0))
            max_response_time = float(response_data.get('max_response_time', 0))
            min_response_time = float(response_data.get('min_response_time', 0))
            p50_response_time = float(response_data.get('p50_response_time', 0))
            p95_response_time = float(response_data.get('p95_response_time', 0))
            p99_response_time = float(response_data.get('p99_response_time', 0))

            # 에러율 조합
            max_err = float(error_result[0]['max_err'] or 0) if error_result else 0.0
            min_err = float(error_result[0]['min_err'] or 0) if error_result else 0.0
            avg_err = float(error_result[0]['avg_err'] or 0) if error_result else 0.0
            
            # Duration 계산 (초 단위)
            test_duration = 0.0
            if start_time_result and end_time_result:
                from datetime import datetime
                
                start_time_str = start_time_result[0]['time']
                end_time_str = end_time_result[0]['time']
                
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                test_duration = (end_time - start_time).total_seconds()
                
                # 디버깅 로그 추가
                logger.debug(f"Scenario {scenario_identifier} - Start: {start_time}, End: {end_time}, Duration: {test_duration}s")
            else:
                logger.warning(f"Scenario {scenario_identifier} - Could not get start/end times")
            
            # TPS 및 에러율 계산 (Fallback for actual_tps)
            actual_tps = total_requests / test_duration if test_duration > 0 else 0.0
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
            
            # 디버깅 로그 추가
            logger.debug(f"Scenario {scenario_identifier} - Total Requests: {total_requests}, Duration: {test_duration}s, TPS: {actual_tps}")
            
            if actual_tps == 0.0:
                logger.warning(f"Scenario {scenario_identifier} - TPS is 0! Check: total_requests={total_requests}, test_duration={test_duration}")
            
            metrics = {
                'total_requests': total_requests,
                'failed_requests': failed_requests,

                'actual_tps': round(actual_tps, 2),  # Calculated TPS as fallback
                'max_tps': round(max_tps, 2),
                'min_tps': round(min_tps, 2),
                'avg_tps': round(avg_tps, 2),

                'avg_response_time': round(avg_response_time, 2),
                'max_response_time': round(max_response_time, 2),
                'min_response_time': round(min_response_time, 2),
                'p50_response_time': round(p50_response_time, 2),
                'p95_response_time': round(p95_response_time, 2),
                'p99_response_time': round(p99_response_time, 2),

                'max_error_rate': round(max_err, 2),
                'min_error_rate': round(min_err, 2),
                'avg_error_rate': round(avg_err, 2),

                'test_duration': round(test_duration, 2)
            }
            
            logger.info(f"Retrieved scenario metrics for scenario '{scenario_identifier}': TPS={actual_tps:.2f}, Error Rate={error_rate:.2f}%")
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving scenario metrics for scenario '{scenario_identifier}': {e}")
            return None

    def get_test_time_range(self, job_name: str) -> Optional[Tuple[datetime, datetime]]:
        """
        테스트의 시작/종료 시간을 조회
        
        Args:
            job_name: Kubernetes Job 이름
            
        Returns:
            (start_time, end_time) 튜플 또는 None
        """
        try:
            start_time_query = f'''
                SELECT * FROM "http_reqs"
                WHERE "job_name" = '{job_name}'
                ORDER BY time ASC LIMIT 1
            '''
            
            end_time_query = f'''
                SELECT * FROM "http_reqs"
                WHERE "job_name" = '{job_name}'
                ORDER BY time DESC LIMIT 1
            '''
            
            start_result = list(self.client.query(start_time_query).get_points())
            end_result = list(self.client.query(end_time_query).get_points())
            
            if not start_result or not end_result:
                logger.warning(f"No time range found for job: {job_name}")
                return None
                
            start_time_str = start_result[0]['time']
            end_time_str = end_result[0]['time']
            
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            
            logger.info(f"Job {job_name} time range: {start_time} ~ {end_time}")
            return (start_time, end_time)
            
        except Exception as e:
            logger.error(f"Error getting time range for job {job_name}: {e}")
            return None

    def get_scenario_names_for_job(self, job_name: str) -> List[str]:
        """
        job_name으로 시나리오 이름들을 조회
        
        Args:
            job_name: Kubernetes Job 이름
            
        Returns:
            시나리오 이름 리스트
        """
        try:
            query = f'''
                SHOW TAG VALUES FROM "http_reqs" 
                WITH KEY = "scenario" 
                WHERE "job_name" = '{job_name}'
            '''
            result = self.client.query(query)
            scenarios = [point['value'] for point in result.get_points() if 'value' in point]
            logger.info(f"Found {len(scenarios)} scenarios for job {job_name}: {scenarios}")
            return scenarios
        except Exception as e:
            logger.error(f"Error getting scenario names for job {job_name}: {e}")
            return []

    def get_interval_metrics(self, job_name: str, start_time: datetime, end_time: datetime, 
                           scenario_name: Optional[str] = None) -> Optional[Dict]:
        """
        특정 시간 구간(10초)에 대한 메트릭 조회
        
        Args:
            job_name: Kubernetes Job 이름
            start_time: 구간 시작 시간
            end_time: 구간 종료 시간  
            scenario_name: 시나리오 이름 (None이면 전체 데이터)
            
        Returns:
            구간 메트릭 딕셔너리 또는 None
        """
        try:
            # 시간 조건 생성
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # 기본 WHERE 조건
            base_where = f'"job_name" = \'{job_name}\' AND time >= \'{start_str}\' AND time < \'{end_str}\''
            if scenario_name:
                base_where += f' AND "scenario" = \'{scenario_name}\''
            
            # TPS 계산 (요청 수 / 10초)
            tps_query = f'''
                SELECT SUM("value") as total_requests
                FROM "http_reqs"
                WHERE {base_where}
            '''
            
            # 에러율 계산
            error_query = f'''
                SELECT SUM("value") as error_requests
                FROM "http_reqs"
                WHERE {base_where} AND "status" !~ /^2../
            '''
            
            # VUS 조회 (구간 내 마지막 값)
            vus_query = f'''
                SELECT LAST("value") as vus
                FROM "vus"
                WHERE {base_where}
            '''
            
            # 응답시간 조회
            response_time_query = f'''
                SELECT 
                    MEAN("value") as avg_response_time,
                    PERCENTILE("value", 95) as p95_response_time,
                    PERCENTILE("value", 99) as p99_response_time
                FROM "http_req_duration"
                WHERE {base_where}
            '''
            
            # 쿼리 실행
            tps_result = list(self.client.query(tps_query).get_points())
            error_result = list(self.client.query(error_query).get_points())
            vus_result = list(self.client.query(vus_query).get_points())
            response_result = list(self.client.query(response_time_query).get_points())
            
            # 결과 처리
            total_requests = int(tps_result[0]['total_requests'] or 0) if tps_result else 0
            error_requests = int(error_result[0]['error_requests'] or 0) if error_result else 0
            vus = int(vus_result[0]['vus'] or 0) if vus_result else 0
            
            # TPS 계산 (10초 구간이므로 /10)
            tps = total_requests / 10.0
            
            # 에러율 계산
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0.0
            
            # 응답시간 처리
            response_data = response_result[0] if response_result else {}
            avg_response_time = float(response_data.get('avg_response_time', 0))
            p95_response_time = float(response_data.get('p95_response_time', 0))
            p99_response_time = float(response_data.get('p99_response_time', 0))
            
            return {
                'tps': round(tps, 1),
                'error_rate': round(error_rate, 2),
                'vus': vus,
                'avg_response_time': round(avg_response_time, 2),
                'p95_response_time': round(p95_response_time, 2),
                'p99_response_time': round(p99_response_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting interval metrics: {e}")
            return None

    def get_test_timeseries_data(self, job_name: str) -> Optional[List[Dict]]:
        """
        테스트 전체 구간을 10초씩 나누어 시계열 데이터 조회
        
        Args:
            job_name: Kubernetes Job 이름
            
        Returns:
            시계열 데이터 리스트 또는 None
            [
                {
                    'timestamp': datetime,
                    'scenario_name': None or str,  # None이면 전체, str이면 해당 시나리오
                    'tps': float,
                    'error_rate': float,
                    'vus': int,
                    'avg_response_time': float,
                    'p95_response_time': float,
                    'p99_response_time': float
                },
                ...
            ]
        """
        try:
            # 테스트 시간 범위 조회
            time_range = self.get_test_time_range(job_name)
            if not time_range:
                logger.error(f"Could not get time range for job: {job_name}")
                return None
                
            start_time, end_time = time_range
            
            # 시나리오 이름들 조회
            scenario_names = self.get_scenario_names_for_job(job_name)
            
            # 10초 단위로 구간 생성
            timeseries_data = []
            current_time = start_time
            interval = timedelta(seconds=10)
            
            while current_time < end_time:
                interval_end = min(current_time + interval, end_time)
                
                # 한국시간으로 변환
                kst = pytz.timezone('Asia/Seoul')
                current_time_kst = current_time.astimezone(kst)
                
                # 전체 데이터 조회
                overall_metrics = self.get_interval_metrics(job_name, current_time, interval_end)
                if overall_metrics:
                    timeseries_data.append({
                        'timestamp': current_time_kst,  # 한국시간으로 저장
                        'scenario_name': None,  # 전체 데이터
                        **overall_metrics
                    })
                
                # 시나리오별 데이터 조회
                for scenario_name in scenario_names:
                    scenario_metrics = self.get_interval_metrics(job_name, current_time, interval_end, scenario_name)
                    if scenario_metrics:
                        timeseries_data.append({
                            'timestamp': current_time_kst,  # 한국시간으로 저장
                            'scenario_name': scenario_name,
                            **scenario_metrics
                        })
                
                current_time = interval_end
            
            logger.info(f"Generated {len(timeseries_data)} timeseries data points for job: {job_name}")
            return timeseries_data
            
        except Exception as e:
            logger.error(f"Error getting test timeseries data for job {job_name}: {e}")
            return None

    def get_cpu_metrics(self, pod_name: str, start_time: datetime, end_time: datetime) -> Optional[List[Dict]]:
        """
        특정 pod의 CPU 사용량 메트릭 조회 (10초 단위)
        
        Args:
            pod_name: Pod 이름
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            CPU 메트릭 데이터 리스트 또는 None
            [
                {
                    'timestamp': datetime,
                    'metric_type': 'cpu',
                    'unit': 'millicores',
                    'value': float
                },
                ...
            ]
        """
        try:
            # 시간 조건 생성
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # CPU 사용량 쿼리 (millicores 단위)
            cpu_query = f'''
                SELECT non_negative_derivative(mean("container_cpu_usage_seconds_total"), 1s) * 1000 as cpu_millicores 
                FROM "cadvisor_metrics" 
                WHERE "pod" = '{pod_name}' AND "container" = '' AND "image" = '' 
                AND time >= '{start_str}' AND time < '{end_str}'
                GROUP BY time(10s) fill(linear) TZ('Asia/Seoul')
            '''
            
            # 쿼리 실행
            result = list(self.client.query(cpu_query).get_points())
            
            if not result:
                logger.warning(f"No CPU metrics found for pod: {pod_name}")
                return None
            
            # 결과 처리
            kst = pytz.timezone('Asia/Seoul')
            cpu_metrics = []
            for point in result:
                if point.get('cpu_millicores') is not None:
                    utc_time = datetime.fromisoformat(point['time'].replace('Z', '+00:00'))
                    kst_time = utc_time.astimezone(kst)
                    cpu_metrics.append({
                        'timestamp': kst_time,  # 한국시간으로 저장
                        'metric_type': 'cpu',
                        'unit': 'millicores',
                        'value': float(point['cpu_millicores'])
                    })
            
            logger.info(f"Retrieved {len(cpu_metrics)} CPU data points for pod: {pod_name}")
            return cpu_metrics
            
        except Exception as e:
            logger.error(f"Error getting CPU metrics for pod {pod_name}: {e}")
            return None

    def get_memory_metrics(self, pod_name: str, start_time: datetime, end_time: datetime) -> Optional[List[Dict]]:
        """
        특정 pod의 Memory 사용량 메트릭 조회 (10초 단위)
        
        Args:
            pod_name: Pod 이름
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            Memory 메트릭 데이터 리스트 또는 None
            [
                {
                    'timestamp': datetime,
                    'metric_type': 'memory',
                    'unit': 'mb',
                    'value': float
                },
                ...
            ]
        """
        try:
            # 시간 조건 생성
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Memory 사용량 쿼리 (MB 단위)
            memory_query = f'''
                SELECT mean("container_memory_working_set_bytes") / 1024 / 1024 as memory_mb 
                FROM "cadvisor_metrics" 
                WHERE "pod" = '{pod_name}' AND "container" = '' AND "image" = '' 
                AND time >= '{start_str}' AND time < '{end_str}'
                GROUP BY time(10s) fill(linear) TZ('Asia/Seoul')
            '''
            
            # 쿼리 실행
            result = list(self.client.query(memory_query).get_points())
            
            if not result:
                logger.warning(f"No Memory metrics found for pod: {pod_name}")
                return None
            
            # 결과 처리
            kst = pytz.timezone('Asia/Seoul')
            memory_metrics = []
            for point in result:
                if point.get('memory_mb') is not None:
                    utc_time = datetime.fromisoformat(point['time'].replace('Z', '+00:00'))
                    kst_time = utc_time.astimezone(kst)
                    memory_metrics.append({
                        'timestamp': kst_time,  # 한국시간으로 저장
                        'metric_type': 'memory',
                        'unit': 'mb',
                        'value': float(point['memory_mb'])
                    })
            
            logger.info(f"Retrieved {len(memory_metrics)} Memory data points for pod: {pod_name}")
            return memory_metrics
            
        except Exception as e:
            logger.error(f"Error getting Memory metrics for pod {pod_name}: {e}")
            return None

    def get_resource_metrics_for_test(self, job_name: str) -> Optional[Dict[str, List[Dict]]]:
        """
        테스트 기간 동안의 모든 관련 pod들의 CPU/Memory 메트릭 조회
        
        Args:
            job_name: Kubernetes Job 이름
            
        Returns:
            pod별 리소스 메트릭 딕셔너리 또는 None
            {
                'pod-name-1': [
                    {
                        'timestamp': datetime,
                        'metric_type': 'cpu' or 'memory',
                        'unit': 'millicores' or 'mb',
                        'value': float
                    },
                    ...
                ],
                ...
            }
        """
        try:
            # 테스트 시간 범위 조회
            time_range = self.get_test_time_range(job_name)
            if not time_range:
                logger.error(f"Could not get time range for job: {job_name}")
                return None
                
            start_time, end_time = time_range
            
            # 5분 여유를 두고 메트릭 수집
            extended_start = start_time - timedelta(minutes=5)
            extended_end = end_time + timedelta(minutes=5)
            
            logger.info(f"Collecting resource metrics for job {job_name} from {extended_start} to {extended_end}")
            
            # 현재는 특정 pod 이름들이 필요하므로, 이 함수는 k6_job_scheduler에서 호출될 때
            # pod 이름들을 매개변수로 받아서 처리하도록 수정이 필요합니다.
            # 지금은 기본 구조만 만들어두겠습니다.
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting resource metrics for job {job_name}: {e}")
            return None