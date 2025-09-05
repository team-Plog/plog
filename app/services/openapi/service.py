from sqlalchemy.orm import Session
from app.db.sqlite.models.project_models import OpenAPISpecModel

def save_openapi_spec(db: Session, openapi_spec_model: OpenAPISpecModel) -> OpenAPISpecModel:
    db.add(openapi_spec_model)
    db.commit()
    db.refresh(openapi_spec_model)

    return openapi_spec_model
