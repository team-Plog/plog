from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse
from app.db.influxdb.database import client
import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


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
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "status" >= '400'
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
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" = '{job_name}'
              AND "scenario" = '{scenario_name}'
              AND "status" >= '400'
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


def collect_metrics_data(job_name: str) -> Dict[str, Any]:
    """모든 메트릭 데이터를 수집하고 포맷팅"""
    logger.info(f"Starting metrics collection for job: {job_name}")
    
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
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall": overall_metrics,
        "scenarios": scenario_list
    }
    
    logger.debug(f"Final result: {result}")
    return result


async def event_stream(job_name: str):
    """k6 메트릭 데이터를 실시간으로 스트리밍"""
    logger.info(f"Starting SSE stream for job: {job_name}")
    
    while True:
        try:
            metrics_data = collect_metrics_data(job_name)
            yield f"data: {json.dumps(metrics_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Error in event_stream: {e}")
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall": {"tps": 0, "vus": 0, "response_time": 0, "error_rate": 0},
                "scenarios": [],
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        await asyncio.sleep(5)


@router.get('/sse/k6data/{job_name}')
async def sse_k6data(
        job_name: str = Path(..., description="테스트 실시간 데이터 추적 용도로 사용할 job 이름"),
):
    """k6 메트릭 데이터를 실시간으로 스트리밍"""
    return StreamingResponse(event_stream(job_name), media_type="text/event-stream")