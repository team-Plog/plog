from sqlalchemy.orm import Session
from app.models.openapi import OpenAPISpec
from app.db.models import OpenAPISpecModel, EndpointModel

async def save_openapi_spec(db: Session, spec: OpenAPISpec) -> OpenAPISpecModel:
    open_api_spec_model = OpenAPISpecModel(
        title=spec.title,
        version=spec.version
    )

    for ep in spec.endpoints:
        endpoint_model = EndpointModel(
            path=ep.path,
            method=ep.method,
            summary=ep.summary,
            description=ep.description
        )
        open_api_spec_model.endpoints.append(endpoint_model)

    db.add(open_api_spec_model)
    db.commit()
    db.refresh(open_api_spec_model)

    return open_api_spec_model
