from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.database import Base

# 중간 테이블 정의
tags_endpoints = Table(
    "tags_endpoints",
    Base.metadata,
    Column("endpoint_id", ForeignKey("endpoints.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True)
)


# OpenAPI 스펙
class OpenAPISpecModel(Base):
    __tablename__ = "openapi_specs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    version = Column(String, nullable=True)

    tags = relationship("TagModel", back_populates="openapi_spec", cascade="all, delete")

# 태그
class TagModel(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    openapi_spec_id = Column(Integer, ForeignKey("openapi_specs.id"))

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
