FROM golang:1.24-alpine3.21 AS builder
WORKDIR $GOPATH/src/go.k6.io/k6

# k6 소스 코드 복사
ADD . .

# git 설치
RUN apk --no-cache add git

# xk6 설치
RUN go install go.k6.io/xk6/cmd/xk6@latest

# xk6-output-influxdb 확장을 위한 디렉토리 생성 및 클론
# 이 경로는 github.com/grafana/xk6-output-influxdb 와 일치해야 합니다.
WORKDIR $GOPATH/src/github.com/grafana/xk6-output-influxdb
RUN git clone https://github.com/grafana/xk6-output-influxdb.git .

# 다시 k6 워크디렉토리로 돌아와서 빌드
WORKDIR $GOPATH/src/go.k6.io/k6
RUN xk6 build --with github.com/grafana/xk6-output-influxdb=. --output /tmp/k6

FROM alpine:3.21
RUN apk add --no-cache ca-certificates && \
    adduser -D -u 12345 -g 12345 k6
COPY --from=builder /tmp/k6 /usr/bin/k6

USER 12345
WORKDIR /home/k6
ENTRYPOINT ["k6"]