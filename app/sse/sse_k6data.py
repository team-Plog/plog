from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.db.influxdb.database import client
import asyncio
import json

router = APIRouter()

async def event_stream():
    while True:
        result = client.query(
            '''
            SELECT COUNT("value")
            FROM "http_reqs"
            WHERE time > now() - 10s
            GROUP BY time(1s) fill(0)
            ORDER BY time DESC
            '''
        )

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
            yield f"data: {json.dumps({"time": None, "tps": 0})}\n\n"
        await asyncio.sleep(5)   # 1초마다 전송


@router.get('/sse/k6data')
async def sse_k6data():
    return StreamingResponse(event_stream(), media_type="text/event-stream")