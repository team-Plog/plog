from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.sqlite.database import Base

# 중간 테이블 endpoints <-> tags
tags_endpoints = Table(
    "tag_endpoint",
    Base.metadata,
    Column("endpoint_id", ForeignKey("endpoint.id"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id"), primary_key=True)
)

# 프로젝트
class ProjectModel(Base):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    summary = Column(String)
    description = Column(Text)
    openapi_specs = relationship("OpenAPISpecModel", back_populates="project")
    test_histories = relationship("TestHistoryModel", back_populates="project")

# OpenAPI 스펙(서버)
class OpenAPISpecModel(Base):
    __tablename__ = "openapi_spec"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    version = Column(String, nullable=True)
    base_url = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("project.id"))

    project = relationship("ProjectModel", back_populates="openapi_specs")
    tags = relationship("TagModel", back_populates="openapi_spec", cascade="all, delete")
    server_infras = relationship("ServerInfraModel", back_populates="openapi_spec")

# 서버와 연결된 POD 정보
class ServerInfraModel(Base):
    __tablename__ = "server_infra"
    id = Column(Integer, primary_key=True, index=True)
    open_api_spec_id = Column(Integer, ForeignKey("openapi_spec.id"))
    openapi_spec = relationship("OpenAPISpecModel", back_populates="server_infras")
    resource_type = Column(String, nullable=True) # POD, DEPLOYMENT, SERVICE
    environment = Column(String, nullable=True) # K3S, ONPREMISE, LOCAL
    service_type = Column(String, nullable=True) # SERVER, DATABASE
    name = Column(String, nullable=True) # RESOURCE NAME
    namespace = Column(String, nullable=True)


# 태그
class TagModel(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    openapi_spec_id = Column(Integer, ForeignKey("openapi_spec.id"))

    openapi_spec = relationship("OpenAPISpecModel", back_populates="tags")
    endpoints = relationship("EndpointModel", secondary=tags_endpoints, back_populates="tags")

# 엔드포인트
class EndpointModel(Base):
    __tablename__ = "endpoint"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=True)
    method = Column(String, nullable=True)
    summary = Column(Text)
    description = Column(Text)

    tags = relationship("TagModel", secondary=tags_endpoints, back_populates="endpoints")
    scenarios = relationship("ScenarioHistoryModel", back_populates="endpoint")
    parameters = relationship("ParameterModel", back_populates="endpoint", cascade="all, delete")

# 파라미터
class ParameterModel(Base):
    __tablename__ = "parameter"
    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoint.id"), nullable=False)
    param_type = Column(String, nullable=False)     # path, query, requestBody
    name = Column(String, nullable=False)           # 파라미터 key name
    required = Column(Boolean, nullable=False, default=False)  # true, false
    value_type = Column(String, nullable=True)      # integer, string, array, object etc.
    title = Column(String, nullable=True)           # 값에 대한 설명
    description = Column(Text, nullable=True)       # 값에 대한 상세 설명
    value = Column(JSON, nullable=True)             # 실제 값 (다양한 타입 지원)

    endpoint = relationship("EndpointModel", back_populates="parameters")