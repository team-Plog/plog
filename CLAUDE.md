# PLOG (Performance Load test Orchestration Gateway) 프로젝트 가이드

## 프로젝트 개요
**Metric Vault** - 소규모 개발팀을 위한 API 성능 테스트 및 메트릭 수집 플랫폼

### 핵심 목표
- **타겟**: 테스트 프로세스가 없는 소규모 개발팀
- **가치**: 테스트 프로세스 시간 단축을 통한 개발 집중도 향상
- **환경**: k3s 클러스터 기반 test namespace 내 Pod 자동 모니터링

### 아키텍처
- **데이터 플로우**: k6 부하테스트 → InfluxDB → 메트릭 집계 → AI 분석/그래프 시각화
- **핵심 메트릭**: TPS, Response Time, Error Rate, VUS
- **레이어 구조**: API Layer → Service Layer → DB Layer/Util Methods

## 디자인 패턴 및 원칙

### 핵심 패턴
1. **Repository Pattern** - 비동기 DB 계층 분리, Service Layer에서 DB 로직 분리
2. **Strategy Pattern** - OpenAPI 분석 전략 (Direct/SwaggerUI)
3. **Singleton Pattern** - 인스턴스 재사용을 통한 메모리 효율성

### 코딩 원칙
- **단일 책임**: 각 클래스/메서드는 하나의 책임만 가짐
- **응집도 최대화**: 관련 기능을 동일 패키지에 배치
- **메서드 Depth 최소화**: 복잡한 로직을 계층별로 분리

## 프로젝트 구조
```
app/
├── api/                 # API 라우터 (API Layer)
├── services/            # 비즈니스 로직 (Service Layer)
├── repositories/        # Repository 패턴 (NEW)
├── models/sqlite/       # SQLite 모델 및 설정
├── dto/                # 데이터 전송 객체
├── scheduler/          # 백그라운드 작업 스케줄러
├── sse/               # Server-Sent Events
├── common/            # 공통 컴포넌트
├── utils/             # 유틸리티 함수 (NEW)
└── k8s/               # Kubernetes 리소스 관리
```

## 주요 기능
1. **자동 OpenAPI 분석** - 전략 패턴 기반 다양한 소스 지원
2. **k6 부하 테스트** - Kubernetes Job 확장 실행
3. **실시간 모니터링** - SSE 기반 실시간 스트리밍  
4. **메트릭 분석** - 성능 지표 집계 및 분석

### 핵심 함수: analyze_openapi_with_strategy
**위치**: `app/services/openapi/strategy_factory.py:158-161`
- Strategy + Factory Method + Singleton Pattern 조합
- URL 패턴 분석을 통한 자동 전략 선택
- ServerPodScheduler에서 자동 OpenAPI 분석 실행

## 환경 설정
### 핵심 환경변수
- `KUBERNETES_TEST_NAMESPACE=test` - 모니터링 대상 네임스페이스
- `INFLUXDB_*` - 메트릭 저장소 설정
- `K6_*` - 부하 테스트 설정
- `SCHEDULER_*` - 백그라운드 작업 설정

### 리팩토링 권장 사항
1. **메트릭 수집/집계 로직 분리**
2. **스케줄러 공통 로직 통합** (Template Method Pattern)
3. **Service Layer 책임 분리**
4. **Repository Pattern 도입** - 비동기 DB 계층 분리

## 응답 형식 
- app.common.response.response_template.py 를 통하여 응답 
- 에러 발생시 적절한 api_exception을 선택 없다면 생성하여 활용 

---

## 🚀 주요 업데이트 이력

### 2025-09-09: Repository Pattern 구현 및 비동기 DB 계층 도입

#### 📋 구현 목적
- SQLite 비동기 Repository 패턴 도입으로 DB 계층 분리
- Service Layer에서 DB 로직 분리 및 재사용성 향상
- 기존 동기 코드 유지하며 점진적 비동기 마이그레이션 지원

#### 🔧 주요 변경사항
1. **Async SQLite Engine 추가** (`app/models/sqlite/database.py`)
   - aiosqlite 드라이버 사용한 비동기 SQLite 엔진
   - 기존 동기 엔진과 병행 운영으로 점진적 마이그레이션

2. **Base Repository 클래스** (`app/repositories/base_repository.py`)
   - Generic 타입 지원 Repository 기본 클래스
   - CRUD 기본 기능 제공 (get, get_multi, create, update, delete)
   - SQLAlchemy 2.0 style select() 문 사용

3. **Scenario History Repository** (`app/repositories/scenario_history_repository.py`)
   - test_history_id로 시나리오 히스토리 조회 메서드 추가
   - BaseRepository 상속으로 기본 CRUD 기능 자동 제공
   - 싱글톤 패턴 적용으로 인스턴스 재사용성 확보

#### 🎯 핵심 아키텍처
```python
# Generic Repository Pattern
class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]
    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100)
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType)
    
# 도메인별 Repository
class ScenarioHistoryRepository(BaseRepository[ScenarioHistoryModel, ScenarioHistoryCreate, ScenarioHistoryUpdate]):
    async def get_scenario_histories_by_test_history_id(self, db: AsyncSession, test_history_id: int)
```

#### 💡 개발 가이드
- **점진적 마이그레이션**: 기존 sync 코드 유지, 신규는 async Repository 사용
- **의존성 추가 필요**: `pip install aiosqlite`
- **Service Layer 리팩토링**: 기존 직접 DB 호출 → Repository 패턴 적용

#### 📖 Repository Pattern 개발 원칙

**1. AsyncSession 데이터베이스 조회 방식**
```python
# ✅ 권장: Repository + AsyncSession 사용
from app.models import get_async_db
from app.repositories.scenario_history_repository import ScenarioHistoryRepository

async def get_scenarios_by_test_id(test_history_id: int):
    async with get_async_db() as db:
        repo = ScenarioHistoryRepository()
        return await repo.get_scenario_histories_by_test_history_id(db, test_history_id)

# ❌ 기존: 직접 DB 호출 (점진적 마이그레이션 대상)
def get_scenarios_sync(test_history_id: int):
    db = SessionLocal()
    return db.query(ScenarioHistoryModel).filter(...).all()
```

**2. Repository 싱글톤 관리**
- **위치**: `app/dependencies/` 패키지에서 Repository 인스턴스 관리
- **패턴**: Singleton Pattern으로 메모리 효율성 확보
- **호출**: Service Layer에서 dependencies를 통해 Repository 호출

**3. 신규 개발 및 마이그레이션 가이드**
- **신규 기능**: 반드시 AsyncSession + Repository Pattern 사용
- **기존 코드**: 점진적으로 Repository Pattern으로 마이그레이션
- **Service Layer**: DB 로직 분리, Repository 호출로 비즈니스 로직에 집중
- **의존성 주입**: FastAPI의 Depends를 활용한 Repository 주입

---

### 2025-09-08: Pod 리소스 메트릭 수집 기능 추가

#### 📋 구현 목적
CPU/Memory 사용률 계산을 위한 Pod 리소스 request/limit 정보 수집

#### 🔧 주요 변경사항
1. **k8s 패키지 신설** - 서비스 구조 개편 및 `resource_service.py` 신규 추가
2. **DB 스키마 확장** - `TestResourceTimeseriesModel`에 CPU/Memory request/limit 컬럼 추가
3. **Pod 리소스 Spec 수집** - Kubernetes API 직접 호출, 단위 변환 자동화
4. **k6 스케줄러 통합** - 메트릭에 리소스 사양 정보 포함

#### 🎯 핵심 기능
- 직접 Pod Spec 조회로 정확한 리소스 정보 획득
- CPU(millicores), Memory(MB) 단위 자동 변환
- 멀티 컨테이너 Pod의 총 리소스 사양 계산
- nullable 컬럼으로 기존 데이터와 호환성 유지

---

### 2025-09-08: k6 UTF-8 인코딩 오류 해결

#### 📋 문제 상황
k6 Job 실행 시 `Invalid UTF-8 character` 오류 발생

#### 🔧 해결 방안
1. **JSON.stringify() 도입** - 직접 JSON 삽입 → JSON.stringify() 방식 변경
2. **Content-Type 헤더 자동 추가** - application/json 헤더 자동 설정
3. **UTF-8 파일 인코딩** - 명시적 UTF-8 인코딩 지정
4. **유니코드 지원 강화** - ensure_ascii=False 옵션 적용

#### 🎯 결과
UTF-8 인코딩 오류 해결, 한글 등 유니코드 문자 지원, k6 Job 정상 실행

---

### 2025-09-09: SSE 응답 구조 개선 및 Swagger 문서화 강화

#### 📋 구현 목적
SSE 응답 JSON 구조의 일관성 개선 및 Swagger API 문서 개발자 친화성 향상

#### 🔧 주요 변경사항
1. **SSE 응답 구조 개선** - usage/actual_usage/specs 의미별 그룹화
2. **Swagger 문서화 강화** - Pydantic 스키마, JSON 예시, 개발자 가이드
3. **실제 사용량 추가** - 백분율과 절대값 병행 제공

#### 🎯 핵심 기능
- 의미별 그룹화로 일관성 확보
- 새로운 메트릭 추가시 해당 그룹에 추가 가능한 확장성
- 클라이언트에서 데이터 구조 이해 용이성
- Swagger를 통한 명확한 API 사용법 제공

#### 💡 개발자 가이드
- **데이터 접근**: `data.usage.cpu_percent`, `data.actual_usage.cpu_millicores`
- **업데이트 주기**: 5초마다 실시간 스트리밍
- **포함 옵션**: all(전체) | k6_only(k6만) | resources_only(리소스만)

---

### 2025-09-10: 메트릭 계산 유틸리티 구현 및 Resource Summary API 완성

#### 📋 구현 목적
리소스 메트릭 계산 로직의 재사용성 향상 및 테스트 히스토리 리소스 요약 API 완성

#### 🔧 주요 변경사항
1. **MetricsCalculator 유틸리티 신설** (`app/utils/metrics_calculator.py`)
   - 메트릭 통계 계산을 위한 정적 메서드 집합
   - `MetricStats` 데이터클래스로 통계 결과 표준화
   - CPU/Memory 메트릭 분리 처리 및 백분율 계산 지원

2. **Resource Summary API 완성** (`app/api/test_history_router.py`)
   - `GET /{test_history_id}/resource/summary` 엔드포인트 구현
   - MetricsCalculator를 활용한 통계 계산
   - ResponseTemplate 기반 일관된 API 응답

3. **Service Layer 로직 완성** (`app/services/testing/test_history_service.py`)
   - `build_test_history_resources_summary_response()` 함수 완성
   - MetricsCalculator 통합으로 계산 로직 분리

#### 🎯 핵심 아키텍처
```python
# MetricStats 데이터클래스
@dataclass
class MetricStats:
    max_value: float
    min_value: float 
    avg_value: float
    count: int

# MetricsCalculator 정적 메서드
class MetricsCalculator:
    @staticmethod
    def calculate_basic_stats(values: List[float]) -> MetricStats
    
    @staticmethod
    def calculate_resource_summary(resources: List) -> Dict[str, MetricStats]
    
    @staticmethod
    def calculate_percentage_stats(actual_values: List[float], limit_values: List[float]) -> MetricStats
```

#### 💡 핵심 기능
- **분리된 메트릭 처리**: CPU/Memory 메트릭을 별도 레코드에서 추출하여 통합 통계 계산
- **백분율 계산**: 실제 사용량 대비 제한값 백분율 자동 계산
- **재사용성**: Service Layer에서 중복 계산 로직 제거, 유틸리티 함수로 통합
- **데이터 검증**: 빈 값 처리 및 안전한 계산 로직

#### 🔧 API 응답 형식
```json
{
  "success": true,
  "message": "테스트 리소스 요약 정보 조회 성공",
  "data": {
    "cpu": {
      "max_value": 85.5,
      "min_value": 12.3,
      "avg_value": 45.2,
      "count": 150
    },
    "memory": {
      "max_value": 78.9,
      "min_value": 25.1,
      "avg_value": 52.3,
      "count": 150
    }
  }
}
```

#### 📖 개발 가이드
- **계산 로직 재사용**: MetricsCalculator 정적 메서드 활용으로 코드 중복 제거
- **메트릭 타입별 처리**: `extract_metric_values()` 메서드로 CPU/Memory 분리 처리
- **Service Layer 단순화**: 복잡한 계산 로직을 유틸리티로 분리하여 비즈니스 로직에 집중
- **확장성**: 새로운 메트릭 타입 추가시 MetricsCalculator에 메서드 추가로 확장 가능

#### 🎯 아키텍처 개선점
- **관심사 분리**: 계산 로직과 비즈니스 로직의 명확한 분리
- **테스트 용이성**: 정적 메서드로 단위 테스트 작성 용이
- **코드 재사용성**: 다른 Service에서도 MetricsCalculator 재사용 가능
- **유지보수성**: 계산 로직 변경시 한 곳에서만 수정하면 되는 구조