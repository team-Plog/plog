from fastapi import APIRouter, Path, Query
from fastapi.responses import StreamingResponse
from app.db.influxdb.database import client
import asyncio
import json
import logging
import pytz
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.sse.pod_spec_cache import get_pod_spec_cache
from app.sse.metrics_buffer import SmartMetricsBuffer
from app.db.sqlite.database import SessionLocal
from app.services.testing.test_history_service import get_test_history_by_job_name

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
kst = pytz.timezone('Asia/Seoul')


def get_scenario_names(job_name: str) -> List[str]:
    """job_name으로 활성 시나리오 이름들을 조회"""
    try:
        query = f'''
            SHOW TAG VALUES FROM "http_reqs" 
            WITH KEY = "scenario" 
            WHERE "job_name" = '{job_name}'
        '''
        result = client.query(query)
        scenarios = [point['value'] for point in result.get_points() if 'value' in point]
        logger.info(f"Total scenarios found: {len(scenarios)} -> {scenarios}")
        return scenarios
    except Exception as e:
        logger.error(f"Error in get_scenario_names: {e}")
        return []


def get_overall_tps(job_name: str) -> float:
    """전체 TPS 조회"""
    try:
        query = f'''
            SELECT COUNT("value") as total_requests
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('total_requests'):
            total_requests = points[0]['total_requests']
            tps = total_requests / 10.0
            return round(tps, 1)
        return 0.0
    except Exception as e:
        logger.error(f"Error in get_overall_tps: {e}")
        return 0.0


def get_overall_vus(job_name: str) -> int:
    """전체 활성 Virtual Users 조회"""
    try:
        query = f'''
            SELECT LAST("value") as vus
            FROM "vus"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('vus') is not None:
            return int(points[0]['vus'])
        return 0
    except Exception as e:
        logger.error(f"Error in get_overall_vus: {e}")
        return 0


def get_overall_latency(job_name: str) -> float:
    """전체 평균 응답시간 조회"""
    try:
        query = f'''
            SELECT MEAN("value") as latency
            FROM "http_req_duration"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('latency') is not None:
            return round(points[0]['latency'], 2)
        return 0.0
    except Exception as e:
        logger.error(f"Error in get_overall_latency: {e}")
        return 0.0


def get_overall_error_rate(job_name: str) -> float:
    """전체 오류율 조회"""
    try:
        total_query = f'''
            SELECT COUNT("value") as total
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
        '''
        error_query = f'''
            SELECT COUNT("value") as errors
            FROM "http_req_failed"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
        '''
        
        total_result = client.query(total_query)
        error_result = client.query(error_query)
        
        total_points = list(total_result.get_points())
        error_points = list(error_result.get_points())
        
        total_count = total_points[0]['total'] if total_points else 0
        error_count = error_points[0]['errors'] if error_points else 0
        
        if total_count == 0:
            return 0.0
            
        return round((error_count / total_count) * 100, 2)
    except Exception as e:
        logger.error(f"Error in get_overall_error_rate: {e}")
        return 0.0


def get_scenario_tps(job_name: str, scenario_name: str) -> float:
    """시나리오별 TPS 조회"""
    try:
        query = f'''
            SELECT COUNT("value") as total_requests
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "scenario" = '{scenario_name}'
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('total_requests'):
            total_requests = points[0]['total_requests']
            tps = total_requests / 10.0
            return round(tps, 1)
        return 0.0
    except Exception as e:
        logger.error(f"Error in get_scenario_tps for '{scenario_name}': {e}")
        return 0.0


def get_scenario_vus(job_name: str, scenario_name: str) -> int:
    """시나리오별 활성 Virtual Users 조회"""
    try:
        query = f'''
            SELECT LAST("value") as vus
            FROM "vus"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "scenario" = '{scenario_name}'
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('vus') is not None:
            return int(points[0]['vus'])
        
        # 시나리오별 VUS 조회가 실패하면 전체 VUS를 대신 반환
        return get_overall_vus(job_name)
    except Exception as e:
        logger.error(f"Error in get_scenario_vus for '{scenario_name}': {e}")
        return 0


def get_scenario_latency(job_name: str, scenario_name: str) -> float:
    """시나리오별 평균 응답시간 조회"""
    try:
        query = f'''
            SELECT MEAN("value") as latency
            FROM "http_req_duration"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "scenario" = '{scenario_name}'
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('latency') is not None:
            return round(points[0]['latency'], 2)
        return 0.0
    except Exception as e:
        logger.error(f"Error in get_scenario_latency for '{scenario_name}': {e}")
        return 0.0


def get_scenario_error_rate(job_name: str, scenario_name: str) -> float:
    """시나리오별 오류율 조회"""
    try:
        total_query = f'''
            SELECT COUNT("value") as total
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "scenario" = '{scenario_name}'
        '''
        error_query = f'''
            SELECT COUNT("value") as errors
            FROM "http_req_failed"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "scenario" = '{scenario_name}'
        '''
        
        total_result = client.query(total_query)
        error_result = client.query(error_query)
        
        total_points = list(total_result.get_points())
        error_points = list(error_result.get_points())

        total_count = total_points[0]['total'] if total_points else 0
        error_count = error_points[0]['errors'] if error_points else 0

        if total_count == 0:
            return 0.0
            
        return round((error_count / total_count) * 100, 2)
    except Exception as e:
        logger.error(f"Error in get_scenario_error_rate for '{scenario_name}': {e}")
        return 0.0


def collect_metrics_data(job_name: str, include_resources: bool = True) -> Dict[str, Any]:
    """모든 메트릭 데이터를 수집하고 포맷팅 (k6 + resource 메트릭)"""
    logger.info(f"Starting metrics collection for job: {job_name} (include_resources={include_resources})")
    
    # 1. 기존 k6 메트릭 수집
    scenarios = get_scenario_names(job_name)
    
    overall_metrics = {
        "tps": get_overall_tps(job_name),
        "vus": get_overall_vus(job_name), 
        "response_time": get_overall_latency(job_name),
        "error_rate": get_overall_error_rate(job_name)
    }
    
    scenario_list = []
    for scenario in scenarios:
        scenario_list.append({
            "name": scenario,
            "scenario_tag": scenario,
            "tps": get_scenario_tps(job_name, scenario),
            "vus": get_scenario_vus(job_name, scenario),
            "response_time": get_scenario_latency(job_name, scenario),
            "error_rate": get_scenario_error_rate(job_name, scenario)
        })
    
    # 2. 기본 응답 구조
    result = {
        "timestamp": datetime.now(kst).isoformat(),
        "overall": overall_metrics,
        "scenarios": scenario_list
    }
    
    # 3. Resource 메트릭 추가 (옵션)
    if include_resources:
        try:
            resource_metrics = collect_resource_metrics(job_name)
            if resource_metrics:
                result["resources"] = resource_metrics  # 직접 배열 할당
                logger.debug(f"Added {len(resource_metrics)} resource metrics for job {job_name}")
            else:
                # 리소스 메트릭이 없는 경우 빈 배열
                result["resources"] = []
                logger.debug(f"No resource metrics available for job {job_name}, using empty array")
        except Exception as e:
            logger.error(f"Error collecting resource metrics for job {job_name}: {e}")
            # 에러 발생 시 빈 배열
            result["resources"] = []
    
    logger.debug(f"Final result for {job_name}: k6_scenarios={len(scenario_list)}, "
                f"resources_included={'yes' if include_resources and result.get('resources') else 'no'}")
    
    return result


async def event_stream(job_name: str, include_resources: bool = True):
    """k6 메트릭 데이터를 실시간으로 스트리밍 (resource 메트릭 포함)"""
    logger.info(f"Starting SSE stream for job: {job_name} (include_resources={include_resources})")
    
    while True:
        try:
            metrics_data = collect_metrics_data(job_name, include_resources)
            yield f"data: {json.dumps(metrics_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Error in event_stream: {e}")
            error_data = {
                "timestamp": datetime.now(kst).isoformat(),
                "overall": {"tps": 0, "vus": 0, "response_time": 0, "error_rate": 0},
                "scenarios": [],
                "error": str(e)
            }
            
            # 에러 시에도 resources 구조 포함 (요청된 경우)
            if include_resources:
                error_data["resources"] = []  # 에러 시 빈 배열
                
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        await asyncio.sleep(5)


@router.get('/sse/k6data/{job_name}')
async def sse_k6data(
        job_name: str = Path(..., description="테스트 실시간 데이터 추적 용도로 사용할 job 이름"),
        include: str = Query("all", description="포함할 메트릭 타입: all(기본)|k6_only|resources_only")
):
    """
    k6 + Resource 메트릭 데이터를 실시간으로 스트리밍
    
    Parameters:
    - job_name: 테스트 Job 이름
    - include: 포함할 메트릭 타입
        - "all" (기본): k6 + resource 메트릭 모두 포함
        - "k6_only": k6 메트릭만 포함
        - "resources_only": resource 메트릭만 포함 (향후 구현)
    
    Response format:
    {
        "timestamp": "2025-09-08T...",
        "overall": {...},           // k6 메트릭
        "scenarios": [...],         // k6 시나리오별 메트릭
        "resources": {              // resource 메트릭 (include=all일 때)
            "overall": {
                "cpu_usage_percent": 45.2,
                "memory_usage_percent": 67.8,
                "cpu_is_predicted": false,
                "memory_is_predicted": false
            },
            "servers": [...],
            "prediction_info": {...}
        }
    }
    """
    # 파라미터 검증 및 변환
    include = include.lower()
    valid_includes = {"all", "k6_only", "resources_only"}
    
    if include not in valid_includes:
        logger.warning(f"Invalid include parameter '{include}', using 'all'")
        include = "all"
    
    # include 파라미터에 따른 설정
    if include == "all":
        include_resources = True
    elif include == "k6_only":
        include_resources = False
    elif include == "resources_only":
        # TODO: 향후 resources_only 구현시 별도 로직 추가
        logger.info(f"resources_only mode requested for job {job_name} (not yet fully implemented)")
        include_resources = True
    else:
        include_resources = True  # fallback
    
    logger.info(f"Starting SSE for job {job_name} with include={include} (resources={include_resources})")
    
    return StreamingResponse(
        event_stream(job_name, include_resources), 
        media_type="text/event-stream"
    )


# ========== Resource Metrics Functions ==========

# 글로벌 메트릭 버퍼들 (job_name -> pod_name -> metric_type -> SmartMetricsBuffer)
resource_metrics_buffers: Dict[str, Dict[str, Dict[str, SmartMetricsBuffer]]] = {}


def get_pod_cpu_usage_millicores(pod_name: str) -> Optional[float]:
    """
    Pod의 현재 CPU 사용량 조회 (millicores 단위)
    
    Args:
        pod_name: Pod 이름
        
    Returns:
        float: CPU 사용량 (millicores 단위) 또는 None
    """
    try:
        query = f'''
            SELECT non_negative_derivative(last("container_cpu_usage_seconds_total"), 1s) * 1000 as cpu_millicores
            FROM "cadvisor_metrics"
            WHERE "pod" = '{pod_name}' AND "container" = '' AND "image" = ''
            AND time > now() - 30s
            GROUP BY "pod" fill(null)
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('cpu_millicores') is not None:
            cpu_millicores = float(points[0]['cpu_millicores'])
            logger.debug(f"Pod {pod_name} CPU usage: {cpu_millicores:.2f} millicores")
            return cpu_millicores
        else:
            logger.debug(f"No CPU data found for pod {pod_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error querying CPU usage for {pod_name}: {e}")
        return None


def get_pod_memory_usage_mb(pod_name: str) -> Optional[float]:
    """
    Pod의 현재 Memory 사용량 조회 (MB 단위)
    
    Args:
        pod_name: Pod 이름
        
    Returns:
        float: Memory 사용량 (MB 단위) 또는 None
    """
    try:
        query = f'''
            SELECT last("container_memory_usage_bytes") as memory_bytes
            FROM "cadvisor_metrics"
            WHERE "pod" = '{pod_name}' AND "container" = '' AND "image" = ''
            AND time > now() - 30s
            GROUP BY "pod"
        '''
        result = client.query(query)
        points = list(result.get_points())
        
        if points and points[0].get('memory_bytes') is not None:
            memory_bytes = float(points[0]['memory_bytes'])
            memory_mb = memory_bytes / (1024 * 1024)  # bytes to MB
            logger.debug(f"Pod {pod_name} Memory usage: {memory_mb:.2f} MB")
            return memory_mb
        else:
            logger.debug(f"No Memory data found for pod {pod_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error querying memory usage for {pod_name}: {e}")
        return None


def calculate_resource_usage_percentage(actual_usage: Optional[float], limit_value: Optional[float], 
                                      resource_type: str) -> float:
    """
    실제 사용량을 limit 기준 백분율로 계산
    
    Args:
        actual_usage: 실제 사용량 (millicores 또는 MB)
        limit_value: limit 값 (millicores 또는 MB)
        resource_type: 'cpu' 또는 'memory'
        
    Returns:
        float: 사용률 백분율 (0-100%)
    """
    if actual_usage is None or limit_value is None or limit_value == 0:
        logger.debug(f"Cannot calculate {resource_type} percentage: "
                    f"usage={actual_usage}, limit={limit_value}")
        return 0.0
    
    usage_percentage = (actual_usage / limit_value) * 100
    result = min(100.0, max(0.0, usage_percentage))  # 0-100% 범위 제한
    
    logger.debug(f"{resource_type.upper()} usage: {actual_usage:.2f} / {limit_value:.2f} "
                f"= {result:.2f}%")
    
    return result


def get_pod_resource_usage_percentage(job_name: str, pod_name: str, service_type: str = "SERVER") -> Optional[Dict[str, Any]]:
    """
    Pod의 CPU/Memory 사용률을 백분율로 조회 (예측 포함)
    
    Args:
        job_name: Job 이름
        pod_name: Pod 이름
        service_type: 서비스 유형 (SERVER, DATABASE)
        
    Returns:
        Dict containing usage percentages and metadata
    """
    try:
        # 1. Pod spec 조회 (캐시 활용)
        pod_spec_cache = get_pod_spec_cache()
        resource_specs = pod_spec_cache.get_pod_spec(pod_name)
        
        if not resource_specs:
            logger.warning(f"No resource specs found for pod {pod_name}")
            return None
        
        # 2. 실제 사용량 조회
        actual_cpu = get_pod_cpu_usage_millicores(pod_name)
        actual_memory = get_pod_memory_usage_mb(pod_name)
        
        # 3. 메트릭 버퍼 초기화 (필요시)
        if job_name not in resource_metrics_buffers:
            resource_metrics_buffers[job_name] = {}
        
        if pod_name not in resource_metrics_buffers[job_name]:
            resource_metrics_buffers[job_name][pod_name] = {
                'cpu': SmartMetricsBuffer(f"{pod_name}_cpu", "percentage"),
                'memory': SmartMetricsBuffer(f"{pod_name}_memory", "percentage")
            }
        
        buffers = resource_metrics_buffers[job_name][pod_name]
        
        # 4. CPU 사용률 계산/예측
        if actual_cpu is not None:
            cpu_percent = calculate_resource_usage_percentage(
                actual_cpu, resource_specs.get('cpu_limit_millicores'), 'cpu'
            )
            buffers['cpu'].add_value(cpu_percent, predicted=False)
            cpu_is_predicted = False
        else:
            cpu_percent = buffers['cpu'].predict_next()
            if cpu_percent is not None:
                buffers['cpu'].add_value(cpu_percent, predicted=True)
                cpu_is_predicted = True
            else:
                cpu_percent = 0.0
                cpu_is_predicted = False
        
        # 5. Memory 사용률 계산/예측
        if actual_memory is not None:
            memory_percent = calculate_resource_usage_percentage(
                actual_memory, resource_specs.get('memory_limit_mb'), 'memory'
            )
            buffers['memory'].add_value(memory_percent, predicted=False)
            memory_is_predicted = False
        else:
            memory_percent = buffers['memory'].predict_next()
            if memory_percent is not None:
                buffers['memory'].add_value(memory_percent, predicted=True)
                memory_is_predicted = True
            else:
                memory_percent = 0.0
                memory_is_predicted = False
        
        return {
            'pod_name': pod_name,
            'service_type': service_type,
            'cpu_usage_percent': round(cpu_percent, 2) if cpu_percent is not None else 0.0,
            'memory_usage_percent': round(memory_percent, 2) if memory_percent is not None else 0.0,
            'cpu_is_predicted': cpu_is_predicted,
            'memory_is_predicted': memory_is_predicted,
            'specs': {
                'cpu_limit_millicores': resource_specs.get('cpu_limit_millicores'),
                'memory_limit_mb': resource_specs.get('memory_limit_mb')
            },
            'prediction_info': {
                'cpu_streak': buffers['cpu'].prediction_streak,
                'memory_streak': buffers['memory'].prediction_streak,
                'cpu_confidence': buffers['cpu'].confidence[-1] if buffers['cpu'].confidence else 1.0,
                'memory_confidence': buffers['memory'].confidence[-1] if buffers['memory'].confidence else 1.0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting resource usage for pod {pod_name}: {e}")
        return None


def get_job_pods_with_service_types(job_name: str) -> List[Dict[str, str]]:
    """
    Job 이름으로 관련 Pod 목록과 service_type 조회
    
    간단한 경로: job_name → TestHistory → ScenarioHistory → ServerInfra
    
    Args:
        job_name: Job 이름
        
    Returns:
        List[Dict]: [{"pod_name": "api-server-123", "service_type": "SERVER"}, ...]
    """
    db = SessionLocal()
    try:
        # 1. job_name으로 TestHistory 조회
        test_history = get_test_history_by_job_name(db, job_name)
        if not test_history:
            logger.warning(f"No test history found for job: {job_name}")
            return []
        
        pod_info_list = []
        processed_pods = set()  # 중복 제거용
        
        # 2. TestHistory의 scenario들에서 각각의 server_infra 정보 추출
        for scenario in test_history.scenarios:
            try:
                endpoint = scenario.endpoint
                if not endpoint or not endpoint.openapi_spec_version:
                    logger.debug(f"Skipping scenario {scenario.id} - missing endpoint or spec version")
                    continue
                
                openapi_spec = endpoint.openapi_spec_version.openapi_spec
                if not openapi_spec or not openapi_spec.server_infras:
                    logger.debug(f"Skipping scenario {scenario.id} - missing openapi spec or server infras")
                    continue
                
                # 3. 각 server_infra에서 Pod 정보 추출
                for server_infra in openapi_spec.server_infras:
                    if server_infra.name and server_infra.name not in processed_pods:
                        pod_info = {
                            "pod_name": server_infra.name,
                            "service_type": server_infra.service_type or "SERVER"  # 기본값 SERVER
                        }
                        pod_info_list.append(pod_info)
                        processed_pods.add(server_infra.name)
                        
                        logger.debug(f"Found pod: {server_infra.name} (type: {server_infra.service_type})")
                
            except Exception as e:
                logger.error(f"Error processing scenario {scenario.id}: {e}")
                continue
        
        logger.info(f"Found {len(pod_info_list)} pods for job {job_name}: "
                   f"{[p['pod_name'] for p in pod_info_list]}")
        
        return pod_info_list
        
    except Exception as e:
        logger.error(f"Error getting pods for job {job_name}: {e}")
        return []
    finally:
        db.close()


def get_job_pods_from_scenarios(job_name: str) -> List[str]:
    """
    Job의 시나리오에서 관련 Pod들을 추출 (Pod 이름만 반환)
    
    Args:
        job_name: Job 이름
        
    Returns:
        List[str]: Pod 이름 목록
    """
    pod_info_list = get_job_pods_with_service_types(job_name)
    pod_names = [pod_info["pod_name"] for pod_info in pod_info_list]
    
    logger.info(f"Extracted pod names for job {job_name}: {pod_names}")
    return pod_names


def collect_resource_metrics(job_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Job의 전체 리소스 메트릭 수집 (플랫 배열로 반환)
    
    Args:
        job_name: Job 이름
        
    Returns:
        List[Dict] containing individual pod metrics or None if no data
    """
    try:
        # 1. DB에서 Pod 목록과 service_type 조회
        pod_info_list = get_job_pods_with_service_types(job_name)
        
        if not pod_info_list:
            logger.warning(f"No pods found for job {job_name}")
            return None
        
        # 2. 개별 Pod 메트릭 수집 (service_type 포함)
        pod_metrics = []
        
        for pod_info in pod_info_list:
            pod_name = pod_info["pod_name"]
            service_type = pod_info["service_type"]
            
            pod_metric = get_pod_resource_usage_percentage(job_name, pod_name, service_type)
            if pod_metric:
                pod_metrics.append(pod_metric)
                logger.debug(f"Collected metrics for {pod_name} (type: {service_type})")
            else:
                logger.warning(f"Failed to collect metrics for {pod_name}")
        
        if not pod_metrics:
            logger.warning(f"No valid pod metrics for job {job_name}")
            return None
        
        logger.info(f"Collected metrics for {len(pod_metrics)} pods in job {job_name}")
        return pod_metrics
        
    except Exception as e:
        logger.error(f"Error collecting resource metrics for job {job_name}: {e}")
        return None


def cleanup_job_metrics_buffers(job_name: str) -> int:
    """
    Job 완료시 관련 메트릭 버퍼들 정리
    
    Args:
        job_name: 정리할 Job 이름
        
    Returns:
        int: 정리된 버퍼 수
    """
    if job_name in resource_metrics_buffers:
        pod_count = len(resource_metrics_buffers[job_name])
        del resource_metrics_buffers[job_name]
        logger.info(f"Cleaned up resource metrics buffers for job {job_name} ({pod_count} pods)")
        return pod_count
    
    return 0