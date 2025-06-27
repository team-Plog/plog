from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class OpenAPISpecModel(Base):
    __tablename__ = "openapi_specs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    version = Column(String, nullable=False)

    endpoints = relationship("EndpointModel", back_populates="spec", cascade="all, delete")


class EndpointModel(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    summary = Column(Text)
    description = Column(Text)

    spec_id = Column(Integer, ForeignKey("openapi_specs.id"))
    spec = relationship("OpenAPISpecModel", back_populates="endpoints")
