from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from app.db.sqlite.database import Base

# 중간 테이블 endpoints <-> tags
tags_endpoints = Table(
    "tags_endpoints",
    Base.metadata,
    Column("endpoint_id", ForeignKey("endpoints.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True)
)

# 중간 테이블 test_history <-> endpoints
test_history_endpoints = Table(
    "test_histories_endpoints",
    Base.metadata,
    Column("test_history_id", ForeignKey("test_histories.id"), primary_key=True),
    Column("endpoint_id", ForeignKey("endpoints.id"), primary_key=True)
)

# 프로젝트
class ProjectModel(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    summary = Column(String)
    description = Column(Text)
    openapi_specs = relationship("OpenAPISpecModel", back_populates="project")

# OpenAPI 스펙(서버)
class OpenAPISpecModel(Base):
    __tablename__ = "openapi_specs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    version = Column(String, nullable=True)
    base_url = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))

    project = relationship("ProjectModel", back_populates="openapi_specs")
    tags = relationship("TagModel", back_populates="openapi_spec", cascade="all, delete")

# 태그
class TagModel(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    openapi_spec_id = Column(Integer, ForeignKey("openapi_specs.id"))

    # 다대다 관계이기 때문에 back_populates를 복수로 지정
    openapi_spec = relationship("OpenAPISpecModel", back_populates="tags")
    endpoints = relationship("EndpointModel", secondary=tags_endpoints, back_populates="tags")

# 엔드포인트
class EndpointModel(Base):
    __tablename__ = "endpoints"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=True)
    method = Column(String, nullable=True)
    summary = Column(Text)
    description = Column(Text)
    tag_id = Column(Integer, ForeignKey("tags.id"))

    tags = relationship("TagModel", secondary=tags_endpoints, back_populates="endpoints")
    test_histories = relationship("TestHistoryModel", secondary=test_history_endpoints, back_populates="endpoints")

class TestHistoryModel(Base):
    __tablename__ = "test_histories"

    id = Column(Integer, primary_key=True, index=True)
    tested_at = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String(255), nullable=False)
    test_title = Column(String(255), nullable=False)
    test_description = Column(Text, nullable=True)

    endpoints = relationship("EndpointModel", secondary=test_history_endpoints, back_populates="test_histories")
