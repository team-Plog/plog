from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse
from app.db.influxdb.database import client
import asyncio
import json

router = APIRouter()

async def event_stream(job_name: str):
    # job_name like 연산자로 전체 tps ... 정보를 얻을 수 있음
    # job_name 으로 쿼리를 하여 시나리오 이름들을 다 조회
    # 시나리오 별 따로 쿼리를 하여 정보 제공
    # tps, vus, latency, error
    # 4*(1+시나리오 개수) 단 시나리오가 한개가 아닐 때 만큼 쿼리를 해야함.
    # 이 내용을 구현하려면 스크립트 생성시 기록 저장 코드부터 구현
    while True:
        result = client.query(f'''
                    SELECT COUNT("value")
                    FROM "http_reqs"
                    WHERE time > now() - 10s
                      AND "job_name" =~ /{job_name}/
                    GROUP BY time(1s) fill(0)
                    ORDER BY time DESC
                ''')

        data = []
        for point in result.get_points():
            data.append({
                "time": point["time"],
                "tps": point["count"]
            })

        # 마지막 최신 bucket만 전송
        if data:
            yield f"data: {json.dumps(data)}\n\n"
        else:
            data = {"time": None, "tps": 0}
            yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(5)   # 1초마다 전송


@router.get('/sse/k6data/{job_name}')
async def sse_k6data(
        job_name: str = Path(..., description="테스트 실시간 데이터 추적 용도로 사용할 job 이름"),
):
    return StreamingResponse(event_stream(job_name), media_type="text/event-stream")