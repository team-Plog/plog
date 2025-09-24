import pytz
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, DateTime, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from app.models.sqlite.database import Base

def now_kst():
    """KST 타임존으로 현재 시간 반환"""
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst)

class TestHistoryModel(Base):
    __tablename__ = "test_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_tps = Column(Float, nullable=True)
    tested_at = Column(DateTime, default=now_kst)

    job_name = Column(String(255), nullable=True)
    k6_script_file_name = Column(String(255), nullable=True)
    
    # 테스트 완료 상태 및 결과 필드들
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # AI 분석 완료 상태 필드들 (기존 패턴과 동일하게)
    is_analysis_completed = Column(Boolean, default=False)
    analysis_completed_at = Column(DateTime, nullable=True)

    # 프로젝트 id
    project_id = Column(Integer, ForeignKey("project.id"))
    project = relationship("ProjectModel", back_populates="test_histories")
    
    # 전체 테스트 결과 메트릭
    max_tps = Column(Float, nullable=True)
    min_tps = Column(Float, nullable=True)
    avg_tps = Column(Float, nullable=True)

    max_response_time = Column(Float, nullable=True)  # ms
    min_response_time = Column(Float, nullable=True)  # ms
    avg_response_time = Column(Float, nullable=True)  # ms

    p50_response_time = Column(Float, nullable=True)  # ms
    p95_response_time = Column(Float, nullable=True)  # ms
    p99_response_time = Column(Float, nullable=True)  # ms

    max_error_rate = Column(Float, nullable=True)  # %
    min_error_rate = Column(Float, nullable=True)  # %
    avg_error_rate = Column(Float, nullable=True)  # %

    max_vus = Column(Float, nullable=True)
    min_vus = Column(Float, nullable=True)
    avg_vus = Column(Float, nullable=True)

    total_requests = Column(Integer, nullable=True)
    failed_requests = Column(Integer, nullable=True)
    test_duration = Column(Float, nullable=True)  # seconds

    scenarios = relationship("ScenarioHistoryModel", back_populates="test_history", cascade="all, delete-orphan")
    test_metrics = relationship("TestMetricsTimeseriesModel", back_populates="test_history", cascade="all, delete-orphan")


class ScenarioHistoryModel(Base):
    __tablename__ = "scenario_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    # k6 실시간 데이터 추적용
    scenario_tag = Column(String(255), nullable=False)

    endpoint_id = Column(Integer, ForeignKey("endpoint.id"), nullable=False)
    endpoint = relationship("EndpointModel", back_populates="scenarios")

    think_time = Column(Float, default=1.0)
    executor = Column(String(50), nullable=False)
    response_time_target = Column(Float, nullable=True)
    error_rate_target = Column(Float, nullable=True)

    total_requests = Column(Integer, nullable=True)
    failed_requests = Column(Integer, nullable=True)
    test_duration = Column(Float, nullable=True)  # seconds

    # 시나리오 테스트 결과 메트릭
    max_tps = Column(Float, nullable=True)
    min_tps = Column(Float, nullable=True)
    avg_tps = Column(Float, nullable=True)

    max_response_time = Column(Float, nullable=True)  # ms
    min_response_time = Column(Float, nullable=True)  # ms
    avg_response_time = Column(Float, nullable=True)  # ms

    p50_response_time = Column(Float, nullable=True)  # ms
    p95_response_time = Column(Float, nullable=True)  # ms
    p99_response_time = Column(Float, nullable=True)  # ms

    max_error_rate = Column(Float, nullable=True)  # %
    min_error_rate = Column(Float, nullable=True)  # %
    avg_error_rate = Column(Float, nullable=True)  # %

    test_history_id = Column(Integer, ForeignKey("test_history.id"))
    test_history = relationship("TestHistoryModel", back_populates="scenarios")

    stages = relationship("StageHistoryModel", back_populates="scenario", cascade="all, delete-orphan")
    test_parameters = relationship("TestParameterHistoryModel", back_populates="scenario", cascade="all, delete-orphan")
    test_headers = relationship("TestHeaderHistoryModel", back_populates="scenario", cascade="all, delete-orphan")
    test_metrics = relationship("TestMetricsTimeseriesModel", back_populates="scenario", cascade="all, delete-orphan")

class TestParameterHistoryModel(Base):
    __tablename__ = "test_parameter_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)           # 파라미터 이름
    param_type = Column(String, nullable=False)     # path, query, requestBody
    value = Column(String, nullable=False)          # 실제 사용된 값 (문자열)
    
    scenario_id = Column(Integer, ForeignKey("scenario_history.id"))
    scenario = relationship("ScenarioHistoryModel", back_populates="test_parameters")

class TestHeaderHistoryModel(Base):
    __tablename__ = "test_header_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    header_key = Column(String, nullable=False)     # 헤더 키
    header_value = Column(String, nullable=False)   # 헤더 값
    
    scenario_id = Column(Integer, ForeignKey("scenario_history.id"))
    scenario = relationship("ScenarioHistoryModel", back_populates="test_headers")

class TestMetricsTimeseriesModel(Base):
    """10초 단위 시계열 메트릭 데이터 (그래프용)"""
    __tablename__ = "test_metrics_timeseries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 시나리오와 연관관계 (null이면 전체 데이터, 값이 있으면 해당 시나리오 데이터)
    scenario_history_id = Column(Integer, ForeignKey("scenario_history.id"), nullable=True)
    scenario = relationship("ScenarioHistoryModel", back_populates="test_metrics")

    test_history_id = Column(Integer, ForeignKey("test_history.id"), nullable=True)
    test_history = relationship("TestHistoryModel", back_populates="test_metrics")
    
    # 시간 구간 (10초 단위 구간의 시작 시간)
    timestamp = Column(DateTime, nullable=False)
    
    # 메트릭 값들 (10초 구간의 평균/합계 값)
    tps = Column(Float, nullable=True)          # Transactions per second
    error_rate = Column(Float, nullable=True)   # Error rate (%)
    vus = Column(Integer, nullable=True)        # Virtual users
    avg_response_time = Column(Float, nullable=True)  # Average response time (ms)
    p95_response_time = Column(Float, nullable=True)  # P95 response time (ms)
    p99_response_time = Column(Float, nullable=True)  # P99 response time (ms)

class TestResourceTimeseriesModel(Base):
    """서버 리소스 시계열 데이터 (CPU, Memory)"""
    __tablename__ = "test_resource_timeseries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 테스트와 연관관계
    scenario_history_id = Column(Integer, ForeignKey("scenario_history.id"), nullable=True)
    scenario = relationship("ScenarioHistoryModel")
    
    # 서버 인프라와 연관관계
    server_infra_id = Column(Integer, ForeignKey("server_infra.id"), nullable=False)
    server_infra = relationship("ServerInfraModel", back_populates="tests_resources")
    
    # 수집 데이터 종류
    metric_type = Column(String(20), nullable=False)  # 'cpu' or 'memory'
    
    # 단위
    unit = Column(String(20), nullable=False)  # 'millicores' for cpu, 'mb' for memory
    
    # 시간
    timestamp = Column(DateTime, nullable=False)
    
    # 측정 값
    value = Column(Float, nullable=False)
    
    # Resource Spec 정보 (Pod의 request/limit 값)
    cpu_request_millicores = Column(Float, nullable=True)    # CPU 요청량 (millicores)
    cpu_limit_millicores = Column(Float, nullable=True)      # CPU 제한량 (millicores)
    memory_request_mb = Column(Float, nullable=True)         # Memory 요청량 (MB)
    memory_limit_mb = Column(Float, nullable=True)           # Memory 제한량 (MB)

class StageHistoryModel(Base):
    __tablename__ = "stage_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    duration = Column(String(20), nullable=False)
    target = Column(Integer, nullable=False)

    scenario_id = Column(Integer, ForeignKey("scenario_history.id"))
    scenario = relationship("ScenarioHistoryModel", back_populates="stages")


class AnalysisHistoryModel(Base):
    """AI 분석 이력 통합 저장 테이블"""
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 기본 분석 정보
    primary_test_id = Column(Integer, ForeignKey("test_history.id"), nullable=False)
    analysis_category = Column(String(50), nullable=False)  # 'single', 'comprehensive'
    analysis_type = Column(String(50), nullable=False)  # 'tps', 'response_time', 'resource_usage', etc.


    # 분석 결과 (JSON으로 유연하게 저장)
    analysis_result = Column(JSON, nullable=False)

    # 메타데이터
    model_name = Column(String(100), nullable=False)

    # 타임스탬프
    analyzed_at = Column(DateTime, default=now_kst, nullable=False)
    created_at = Column(DateTime, default=now_kst, nullable=False)

    # 관계 설정
    primary_test = relationship("TestHistoryModel", foreign_keys=[primary_test_id], backref="primary_analyses")
