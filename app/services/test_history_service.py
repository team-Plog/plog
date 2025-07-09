from datetime import datetime

from sqlalchemy.orm import Session

from app.db.sqlite.models import TestHistoryModel, EndpointModel
from app.models.load_test_request import LoadTestRequest

def create_test_history(
        request: LoadTestRequest,
        file_name: str,
        db: Session,
):
    test_history = TestHistoryModel(
        tested_at=datetime.utcnow(),
        file_name=file_name,
        test_title=request.title,
        test_description=request.description
    )

    endpoint_ids = {scenario.endpoint_id for scenario in request.scenarios}
    endpoints = db.query(EndpointModel).filter(EndpointModel.id.in_(endpoint_ids)).all()
    test_history.endpoints.extend(endpoints)

    db.add(test_history)
    db.commit()