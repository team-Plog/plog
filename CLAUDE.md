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
│   ├── monitoring/     # 모니터링 서비스 (InfluxDB, MetricsAggregation)
│   ├── testing/        # 테스트 실행 서비스
│   └── infrastructure/ # 인프라 관리 서비스
├── db/                 # 데이터베이스 (DB Layer)
│   ├── sqlite/        # SQLite 모델 및 설정
│   └── influxdb/      # InfluxDB 연결
├── dto/                # 데이터 전송 객체
├── scheduler/          # 백그라운드 작업 스케줄러
├── sse/               # Server-Sent Events
├── common/            # 공통 컴포넌트
└── k8s/               # Kubernetes 리소스 관리 서비스 (NEW)
    ├── k8s_client.py  # Kubernetes API 클라이언트
    ├── k8s_service.py # Job 생성 및 관리
    ├── pod_service.py # Pod 상태 및 정보 조회
    ├── job_service.py # Job 라이프사이클 관리
    ├── service_service.py # Service 및 NodePort 관리
    └── resource_service.py # Pod 리소스 spec 조회 (NEW)
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

---

## 🚀 주요 업데이트 이력

### 2025-09-08: Pod 리소스 메트릭 수집 기능 추가

#### 📋 구현 목적
- CPU/Memory 사용률 계산을 위한 Pod 리소스 request/limit 정보 수집
- 테스트 완료 후 실제 사용량 대비 설정된 리소스 사양 비교 분석 제공

#### 🔧 주요 변경사항

**1. k8s 패키지 신설 및 서비스 이전**
```
기존: app/services/monitoring/
새로운: k8s/
- pod_service.py (이전)
- job_service.py (이전)  
- service_service.py (이전)
- resource_service.py (신규)
- k8s_client.py, k8s_service.py (기존)
```

**2. 데이터베이스 스키마 확장**
`TestResourceTimeseriesModel`에 4개 컬럼 추가:
```python
# Resource Spec 정보 (Pod의 request/limit 값)
cpu_request_millicores = Column(Float, nullable=True)    # CPU 요청량 (millicores)
cpu_limit_millicores = Column(Float, nullable=True)      # CPU 제한량 (millicores)
memory_request_mb = Column(Float, nullable=True)         # Memory 요청량 (MB)
memory_limit_mb = Column(Float, nullable=True)           # Memory 제한량 (MB)
```

**3. Pod 리소스 Spec 수집 서비스 (`k8s/resource_service.py`)**
```python
class ResourceService:
    def get_pod_aggregated_resources(self, pod_name: str) -> Optional[Dict[str, float]]:
        """Pod의 모든 컨테이너 리소스를 합계하여 반환"""
        
    def _parse_cpu_to_millicores(self, cpu_value: str) -> float:
        """CPU 값을 millicores 단위로 변환 (500m → 500, 1 → 1000)"""
        
    def _parse_memory_to_mb(self, memory_value: str) -> float:  
        """Memory 값을 MB 단위로 변환 (512Mi → 512, 1Gi → 1024)"""
```

**4. k6 스케줄러 통합 (`app/scheduler/k6_job_scheduler.py`)**
```python
# Pod의 resource spec 조회
resource_specs = self.resource_service.get_pod_aggregated_resources(pod_name)

# CPU/Memory 메트릭에 resource spec 정보 추가
if cpu_metrics and resource_specs:
    for metric in cpu_metrics:
        metric['cpu_request_millicores'] = resource_specs['cpu_request_millicores']
        metric['cpu_limit_millicores'] = resource_specs['cpu_limit_millicores']
```

#### 🎯 핵심 기능
- **직접 Pod Spec 조회**: InfluxDB 대신 Kubernetes API 직접 호출로 정확한 리소스 정보 획득
- **단위 변환 자동화**: CPU(millicores), Memory(MB) 단위 자동 변환
- **컨테이너 리소스 합계**: 멀티 컨테이너 Pod의 총 리소스 사양 계산
- **백워드 호환성**: nullable 컬럼으로 기존 데이터와 호환성 유지

---

### 2025-09-08: k6 UTF-8 인코딩 오류 해결

#### 📋 문제 상황
k6 Job 실행 시 `Invalid UTF-8 character` 오류 발생:
```
time="2025-09-08T01:53:33Z" level=error msg="GoError: Invalid UTF-8 character"
```

#### 🔧 해결 방안

**1. JSON.stringify() 방식 도입 (`app/services/testing/load_test_service.py`)**
```python
# 수정 전: 직접 JSON 삽입
http.post('url', {raw_json_object}, {headers});

# 수정 후: JSON.stringify() 사용
script_lines.append(f"  const payload = JSON.stringify({url_parts['body']});")
script_lines.append(f"  http.{method}('{url_parts['url']}', payload, {{ headers: {headers_str} }});")
```

**2. Content-Type 헤더 자동 추가**
```python
# Content-Type 헤더 자동 추가
script_lines.append(f"  const requestHeaders = {{...headers, 'Content-Type': 'application/json'}};")
```

**3. UTF-8 파일 저장 보장 (`app/api/load_testing_router.py`)**
```python
# 수정 전
with open(script_path, "w") as f:

# 수정 후  
with open(script_path, "w", encoding="utf-8") as f:
```

**4. JSON 파싱 개선**
```python
# ensure_ascii=False로 유니코드 문자 지원
body = json.dumps(parsed_json, ensure_ascii=False)
```

#### 🎯 결과
- UTF-8 인코딩 오류 해결
- 한글 등 유니코드 문자 지원
- k6 Job 정상 실행 가능

---

### 2025-09-09: SSE 응답 구조 개선 및 Swagger 문서화 강화

#### 📋 구현 목적
- SSE 응답 JSON 구조의 일관성 개선
- 실제 CPU/Memory 사용량 정보 추가 제공
- Swagger API 문서의 개발자 친화성 향상

#### 🔧 주요 변경사항

**1. SSE Resource 메트릭 응답 구조 개선**
```python
# 기존 구조 (최상위 레벨에 산재)
{
  "cpu_usage_percent": 45.2,
  "memory_usage_percent": 67.8,
  "cpu_is_predicted": false,
  "memory_is_predicted": false,
  "specs": {...}
}

# 개선된 구조 (의미별 그룹화)
{
  "usage": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "cpu_is_predicted": false,
    "memory_is_predicted": false
  },
  "actual_usage": {
    "cpu_millicores": 452.5,
    "memory_mb": 678.3
  },
  "specs": {
    "cpu_request_millicores": 500,
    "cpu_limit_millicores": 1000,
    "memory_request_mb": 512,
    "memory_limit_mb": 1024
  }
}
```

**2. Swagger 문서화 강화 (`app/sse/sse_k6data.py`)**
- **Pydantic 스키마 모델**: 타입 안전성과 자동 문서 생성
- **실제 응답 JSON 예시**: 완전한 JSON 구조와 인라인 주석
- **개발자 친화적 description**: 필드별 한 줄 설명과 접근 방법 안내

**3. 실제 사용량 정보 추가**
- `actual_usage` 객체로 실제 CPU(millicores), Memory(MB) 사용량 제공
- 백분율과 함께 절대값도 확인 가능하여 리소스 사용량 분석 용이

#### 🎯 핵심 기능
- **일관성**: 모든 하위 정보가 의미별로 그룹화
- **확장성**: 새로운 메트릭 추가시 해당 그룹에 추가 가능
- **가독성**: 클라이언트에서 데이터 구조 이해 용이
- **문서화**: Swagger를 통한 명확한 API 사용법 제공

#### 💡 개발자 가이드
- **데이터 접근**: `data.usage.cpu_percent`, `data.actual_usage.cpu_millicores`
- **업데이트 주기**: 5초마다 실시간 스트리밍
- **포함 옵션**: all(전체) | k6_only(k6만) | resources_only(리소스만)

---