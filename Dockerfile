# ====== 1단계: 빌드 환경 ======
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

# ====== 2단계: 런타임 환경 ======
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

# 한국 시간대 설정
ENV TZ=Asia/Seoul
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

