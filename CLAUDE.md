# PLOG (Performance Load test Orchestration Gateway) 프로젝트 가이드

## 프로젝트 개요

**Metric Vault** - 소규모 개발팀을 위한 API 성능 테스트 및 메트릭 수집 플랫폼

### 프로젝트 목적
- **타겟 사용자**: 테스트 프로세스가 없는 소규모 개발팀
- **핵심 가치**: 테스트 프로세스 시간 단축을 통한 개발 집중도 향상
- **테스트 환경**: k3s 클러스터 기반 test namespace 내 Pod 자동 모니터링

### 테스트 타겟 환경
- **내부 서버**: k3s test namespace에 배포된 테스트 서버들 (완전 기능)
- **외부 서버**: 서버 등록을 통한 테스트 (부분적 기능 제공)

## 핵심 아키텍처

### 데이터 플로우
```
k6 부하테스트 → InfluxDB → 메트릭 집계 → AI 분석 / 그래프 시각화
```

### 핵심 메트릭
- **TPS** (Transactions Per Second)
- **Response Time** (응답시간)
- **Error Rate** (에러율) 
- **VUS** (Virtual Users)

### 시스템 컴포넌트
1. **FastAPI 서버**: RESTful API 제공
2. **SQLite**: 프로젝트, 엔드포인트, 테스트 메타데이터
3. **InfluxDB**: 시계열 성능 메트릭 데이터
4. **Kubernetes**: k6 부하 테스트 Job 실행 환경
5. **k6**: 부하 테스트 실행 엔진
6. **SSE**: 실시간 메트릭 스트리밍

## 레이어 아키텍처

```
API Layer (Router)
    ↓
Service Layer (Business Logic + External API calls)
    ↓
DB Layer / Util Methods
```

### 레이어 책임
- **API Layer**: 요청/응답 처리, 데이터 검증
- **Service Layer**: 비즈니스 로직, 외부 서비스 호출, 유틸리티 호출
- **DB Layer**: 데이터 영속화, 쿼리 처리
- **Util Methods**: 공통 기능, 헬퍼 함수

## 핵심 함수: analyze_openapi_with_strategy

**위치**: `app/services/openapi/strategy_factory.py:158-161`

### 디자인 패턴 구현

#### 1. Strategy Pattern
```python
# 전략 인터페이스
class OpenAPIAnalysisStrategy(ABC)

# 구체적 전략들
class DirectOpenAPIStrategy    # JSON/YAML 직접 분석
class SwaggerUIStrategy        # Swagger UI 페이지 분석
```

#### 2. Factory Method Pattern
```python
class OpenAPIStrategyFactory:
    @staticmethod
    async def detect_strategy_type(url: str) -> str:
        # URL 패턴 분석하여 전략 결정
    
    @classmethod
    def create_strategy(cls, strategy_type: str):
        # 전략 타입에 따른 Singleton 인스턴스 반환
```

#### 3. Singleton Pattern
```python
# 전략 인스턴스들을 클래스 변수로 관리
_direct_strategy = None
_swagger_ui_strategy = None
```

### 사용법
```python
# ServerPodScheduler에서 자동 OpenAPI 분석
openapi_request = OpenAPISpecRegisterRequest(
    open_api_url=swagger_urls[0],
    project_id=1
)
analysis_result = await analyze_openapi_with_strategy(openapi_request)
```

## 코딩 가이드라인

### 선호하는 디자인 패턴
1. **Singleton Pattern**: 인스턴스 재사용을 통한 메모리 효율성
2. **Strategy Pattern**: 중복 코드 제거, 알고리즘 캡슐화
3. **Template Method Pattern**: 공통 워크플로우의 중복 제거

### 코드 구조 원칙
- **메서드 Depth 최소화**: 복잡한 로직을 계층별로 분리
- **응집도 높은 패키지 관리**: 관련 기능을 동일 패키지에 배치
- **단일 책임 원칙**: 각 클래스/메서드는 하나의 책임만 가짐

### 우선 리팩토링 권장 사항
1. **메트릭 수집/집계 로직 분리**
   - `metrics_aggregation_service.py`에서 데이터 수집과 분석 로직 분리
   
2. **스케줄러 공통 로직 통합**
   - `k6_job_scheduler.py`와 `server_pod_scheduler.py`의 중복 스케줄링 로직
   - Template Method Pattern 적용 검토
   
3. **Service Layer 책임 분리**
   - 일부 서비스에서 여러 책임이 혼재된 부분 개선

## 프로젝트 구조

```
app/
├── api/                 # API 라우터 (API Layer)
├── services/            # 비즈니스 로직 (Service Layer)
│   ├── openapi/        # OpenAPI 분석 서비스
│   ├── monitoring/     # 모니터링 서비스
│   ├── testing/        # 테스트 실행 서비스
│   └── infrastructure/ # 인프라 관리 서비스
├── db/                 # 데이터베이스 (DB Layer)
│   ├── sqlite/        # SQLite 모델 및 설정
│   └── influxdb/      # InfluxDB 연결
├── dto/                # 데이터 전송 객체
├── scheduler/          # 백그라운드 작업 스케줄러
├── sse/               # Server-Sent Events
└── common/            # 공통 컴포넌트
```

## 주요 기능

### 1. 자동 OpenAPI 분석
- Swagger/OpenAPI 문서 자동 파싱
- 태그 기반 엔드포인트 분류
- 전략 패턴을 통한 다양한 소스 지원

### 2. k6 부하 테스트
- GUI 기반 테스트 시나리오 생성
- Kubernetes Job으로 확장 가능한 실행
- 다양한 부하 패턴 지원

### 3. 실시간 모니터링
- Server-Sent Events를 통한 실시간 스트리밍
- k3s test namespace Pod 자동 감지
- InfluxDB 기반 시계열 데이터 수집

### 4. 메트릭 분석
- 성능 지표 집계 및 분석
- AI 기반 테스트 결과 분석 (향후 구현)
- 그래프 기반 시각화

## 환경 설정

### 핵심 환경변수
- `KUBERNETES_TEST_NAMESPACE=test` - 모니터링 대상 네임스페이스
- `INFLUXDB_*` - 메트릭 저장소 설정
- `K6_*` - 부하 테스트 설정
- `SCHEDULER_*` - 백그라운드 작업 설정