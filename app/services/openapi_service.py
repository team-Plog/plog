from sqlalchemy.orm import Session
from app.models.openapi import OpenAPISpec
from app.db.models import OpenAPISpecModel, TagModel, EndpointModel

async def save_openapi_spec(db: Session, spec: OpenAPISpec) -> OpenAPISpecModel:
    openapi_spec_model = OpenAPISpecModel(
        title=spec.title,
        version=spec.version
    )

    # 각 Tag 아래 Endpoint들을 순회하며 저장
    for tag in spec.tags:
        tag_model = TagModel(
            name=tag.name,
            description=tag.description,

        )

        for ep in tag.endpoints:
            endpoint_model = EndpointModel(
                path=ep.path,
                method=ep.method,
                summary=ep.summary,
                description=ep.description,
                tag_id=ep.tag_id
            )
            tag_model.endpoints.append(endpoint_model)

        openapi_spec_model.tags.append(tag_model)

    db.add(openapi_spec_model)
    db.commit()
    db.refresh(openapi_spec_model)

    return openapi_spec_model
