from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse
from app.db.influxdb.database import client
import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter()


def get_scenario_names(job_name: str) -> List[str]:
    """job_name으로 활성 시나리오 이름들을 조회"""
    try:
        result = client.query(f'''
            SHOW TAG VALUES FROM "http_reqs" 
            WITH KEY = "scenario" 
            WHERE "job_name" =~ /{job_name}/
        ''')
        
        scenarios = []
        for point in result.get_points():
            if 'value' in point:
                scenarios.append(point['value'])
        
        return scenarios
    except Exception:
        return []


def get_overall_tps(job_name: str) -> float:
    """전체 TPS 조회"""
    try:
        result = client.query(f'''
            SELECT COUNT("value") as tps
            FROM "http_reqs"
            WHERE time > now() - 10s AND time <= now()
              AND "job_name" =~ /{job_name}/
            GROUP BY time(1s) fill(0)
            ORDER BY time DESC
            LIMIT 1
        ''')
        
        points = list(result.get_points())
        return points[0]['tps'] if points else 0.0
    except Exception:
        return 0.0


def get_overall_vus(job_name: str) -> int:
    """전체 활성 Virtual Users 조회"""
    try:
        result = client.query(f'''
            SELECT MEAN("value") as vus
            FROM "vus"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
            ORDER BY time DESC
            LIMIT 1
        ''')
        
        points = list(result.get_points())
        return int(points[0]['vus']) if points else 0
    except Exception:
        return 0


def get_overall_latency(job_name: str) -> float:
    """전체 평균 응답시간 조회 (ms)"""
    try:
        result = client.query(f'''
            SELECT MEAN("value") as latency
            FROM "http_req_duration"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
            ORDER BY time DESC
            LIMIT 1
        ''')
        
        points = list(result.get_points())
        return round(points[0]['latency'], 2) if points else 0.0
    except Exception:
        return 0.0


def get_overall_error_rate(job_name: str) -> float:
    """전체 오류율 조회 (%)"""
    try:
        # 전체 요청 수
        total_result = client.query(f'''
            SELECT COUNT("value") as total
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
        ''')
        
        # 오류 요청 수 (status >= 400)
        error_result = client.query(f'''
            SELECT COUNT("value") as errors  
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
              AND "status" >= '400'
        ''')
        
        total_points = list(total_result.get_points())
        error_points = list(error_result.get_points())
        
        total_count = total_points[0]['total'] if total_points else 0
        error_count = error_points[0]['errors'] if error_points else 0
        
        if total_count == 0:
            return 0.0
            
        return round((error_count / total_count) * 100, 2)
    except Exception:
        return 0.0


def get_scenario_tps(job_name: str, scenario_name: str) -> float:
    """시나리오별 TPS 조회"""
    try:
        result = client.query(f'''
            SELECT COUNT("value") as tps
            FROM "http_reqs"
            WHERE time > now() - 10s AND time <= now()
              AND "job_name" =~ /{job_name}/
              AND "scenario" = '{scenario_name}'
            GROUP BY time(1s) fill(0)
            ORDER BY time DESC
            LIMIT 1
        ''')
        
        points = list(result.get_points())
        return points[0]['tps'] if points else 0.0
    except Exception:
        return 0.0


def get_scenario_latency(job_name: str, scenario_name: str) -> float:
    """시나리오별 평균 응답시간 조회"""
    try:
        result = client.query(f'''
            SELECT MEAN("value") as latency
            FROM "http_req_duration"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
              AND "scenario" = '{scenario_name}'
            ORDER BY time DESC
            LIMIT 1
        ''')
        
        points = list(result.get_points())
        return round(points[0]['latency'], 2) if points else 0.0
    except Exception:
        return 0.0


def get_scenario_error_rate(job_name: str, scenario_name: str) -> float:
    """시나리오별 오류율 조회"""
    try:
        total_result = client.query(f'''
            SELECT COUNT("value") as total
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
              AND "scenario" = '{scenario_name}'
        ''')
        
        error_result = client.query(f'''
            SELECT COUNT("value") as errors
            FROM "http_reqs"
            WHERE time > now() - 10s
              AND "job_name" =~ /{job_name}/
              AND "scenario" = '{scenario_name}'
              AND "status" >= '400'
        ''')
        
        total_points = list(total_result.get_points())
        error_points = list(error_result.get_points())
        
        total_count = total_points[0]['total'] if total_points else 0
        error_count = error_points[0]['errors'] if error_points else 0
        
        if total_count == 0:
            return 0.0
            
        return round((error_count / total_count) * 100, 2)
    except Exception:
        return 0.0


def collect_metrics_data(job_name: str) -> Dict[str, Any]:
    """모든 메트릭 데이터를 수집하고 포맷팅"""
    
    # 시나리오 목록 조회
    scenarios = get_scenario_names(job_name)
    
    # 전체 메트릭 수집
    overall_metrics = {
        "tps": get_overall_tps(job_name),
        "vus": get_overall_vus(job_name), 
        "latency": get_overall_latency(job_name),
        "error_rate": get_overall_error_rate(job_name)
    }
    
    # 시나리오별 메트릭 수집
    scenario_metrics = {}
    for scenario in scenarios:
        scenario_metrics[scenario] = {
            "tps": get_scenario_tps(job_name, scenario),
            "latency": get_scenario_latency(job_name, scenario),
            "error_rate": get_scenario_error_rate(job_name, scenario)
        }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "overall": overall_metrics,
        "scenarios": scenario_metrics
    }


async def event_stream(job_name: str):
    """k6 메트릭 데이터를 실시간으로 스트리밍"""
    while True:
        try:
            metrics_data = collect_metrics_data(job_name)
            yield f"data: {json.dumps(metrics_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            # 오류 발생 시 기본 데이터 전송
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall": {"tps": 0, "vus": 0, "latency": 0, "error_rate": 0},
                "scenarios": {},
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        await asyncio.sleep(5)


@router.get('/sse/k6data/{job_name}')
async def sse_k6data(
        job_name: str = Path(..., description="테스트 실시간 데이터 추적 용도로 사용할 job 이름"),
):
    return StreamingResponse(event_stream(job_name), media_type="text/event-stream")