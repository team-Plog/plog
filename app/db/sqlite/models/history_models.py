import pytz
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.sqlite.database import Base

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

class StageHistoryModel(Base):
    __tablename__ = "stage_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    duration = Column(String(20), nullable=False)
    target = Column(Integer, nullable=False)

    scenario_id = Column(Integer, ForeignKey("scenario_history.id"))
    scenario = relationship("ScenarioHistoryModel", back_populates="stages")
