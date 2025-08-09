import logging
from typing import Dict, Optional
from influxdb import InfluxDBClient
from app.core.config import settings

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
        전체 테스트 메트릭 조회
        
        Args:
            job_name: Kubernetes Job 이름
            
        Returns:
            전체 테스트 메트릭 딕셔너리 또는 None
            {
                'total_requests': int,
                'failed_requests': int,
                'actual_tps': float,
                'avg_response_time': float,
                'max_response_time': float,
                'min_response_time': float,
                'p50_response_time': float,
                'p95_response_time': float,
                'p99_response_time': float,
                'error_rate': float,
                'max_vus': int,
                'test_duration': float
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
                    AVG(tps) as avg_tps,
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
                    PERCENTILE("value", 50) as p95_response_time,
                    PERCENTILE("value", 95) as p95_response_time,
                    PERCENTILE("value", 99) as p95_response_time
                FROM "http_req_duration"
                WHERE "job_name" = '{job_name}'
            '''
            
            # VU (Virtual Users) 최대값 조회
            vus_query = f'''
                SELECT MAX("value") as max_vus, MIN("value") as min_vus, AVG("value") as avg_vus,
                FROM "vus"
                WHERE "job_name" = '{job_name}'
            '''

            # 에러율 통계 조회
            error_query = f'''
                SELECT MIN("err") AS min_err, MAX("err") AS max_err, AVG("err") AS avg_err
                FROM (
                    SELECT MEAN("value") as error
                    FROM "http_req_failed"
                    WEHRE "job_name" = '{job_name}'
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
                'tps': float,
                'avg_response_time': float,
                'max_response_time': float,
                'min_response_time': float,
                'p95_response_time': float,
                'error_rate': float
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
            
            # 응답 시간 통계 조회
            response_time_query = f'''
                SELECT 
                    MEAN("value") as avg_response_time,
                    MAX("value") as max_response_time,
                    MIN("value") as min_response_time,
                    PERCENTILE("value", 95) as p95_response_time
                FROM "http_req_duration"
                WHERE "scenario" = '{scenario_identifier}'
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
            response_result = list(self.client.query(response_time_query).get_points())
            start_time_result = list(self.client.query(start_time_query).get_points())
            end_time_result = list(self.client.query(end_time_query).get_points())
            
            if not total_result or not total_result[0]['total_requests']:
                logger.warning(f"No metrics found for scenario: {scenario_identifier}")
                return None
            
            # 결과 조합
            total_requests = int(total_result[0]['total_requests'] or 0)
            failed_requests = int(failed_result[0]['failed_requests'] or 0) if failed_result else 0
            
            response_data = response_result[0] if response_result else {}
            avg_response_time = float(response_data.get('avg_response_time', 0))
            max_response_time = float(response_data.get('max_response_time', 0))
            min_response_time = float(response_data.get('min_response_time', 0))
            p95_response_time = float(response_data.get('p95_response_time', 0))
            
            # Duration 계산
            test_duration = 0.0
            if start_time_result and end_time_result:
                from datetime import datetime
                
                start_time_str = start_time_result[0]['time']
                end_time_str = end_time_result[0]['time']
                
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                test_duration = (end_time - start_time).total_seconds()
            
            # TPS 및 에러율 계산
            tps = total_requests / test_duration if test_duration > 0 else 0.0
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
            
            metrics = {
                'total_requests': total_requests,
                'failed_requests': failed_requests,
                'tps': round(tps, 2),
                'avg_response_time': round(avg_response_time, 2),
                'max_response_time': round(max_response_time, 2),
                'min_response_time': round(min_response_time, 2),
                'p95_response_time': round(p95_response_time, 2),
                'error_rate': round(error_rate, 2)
            }
            
            logger.info(f"Retrieved scenario metrics for scenario '{scenario_identifier}': TPS={tps:.2f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving scenario metrics for scenario '{scenario_identifier}': {e}")
            return None