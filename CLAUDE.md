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