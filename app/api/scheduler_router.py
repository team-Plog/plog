import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response.code import SuccessCode
from app.common.response.response_template import ResponseTemplate
from app.db import get_db
from app.scheduler.k6_job_scheduler import get_scheduler
from app.services.testing.test_history_service import get_incomplete_test_histories

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/status",
    summary="스케줄러 상태 조회 API",
    description="k6 Job 스케줄러의 현재 상태와 처리 중인 작업을 조회합니다."
)
async def get_scheduler_status(db: Session = Depends(get_db)):
    """스케줄러 상태 및 처리 중인 Job 정보를 반환합니다."""
    try:
        scheduler = get_scheduler()
        scheduler_status = scheduler.get_scheduler_status()
        
        # 완료되지 않은 테스트 목록 조회
        incomplete_tests = get_incomplete_test_histories(db)
        incomplete_jobs = [
            {
                'job_name': test.job_name,
                'title': test.title,
                'tested_at': test.tested_at.isoformat() if test.tested_at else None,
                'scenario_count': len(test.scenarios)
            }
            for test in incomplete_tests
        ]
        
        result = {
            'scheduler': scheduler_status,
            'incomplete_jobs': incomplete_jobs,
            'incomplete_count': len(incomplete_jobs)
        }
        
        return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, result)
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return ResponseTemplate.fail("SCHEDULER_STATUS_ERROR", str(e))


@router.post(
    "/restart",
    summary="스케줄러 재시작 API",
    description="k6 Job 스케줄러를 재시작합니다. (디버깅/관리 목적)"
)
async def restart_scheduler():
    """스케줄러를 재시작합니다."""
    try:
        scheduler = get_scheduler()
        
        # 기존 스케줄러 중지
        if scheduler.is_running:
            scheduler.stop()
            logger.info("Scheduler stopped for restart")
        
        # 스케줄러 재시작
        scheduler.start()
        logger.info("Scheduler restarted")
        
        return ResponseTemplate.success(
            SuccessCode.SUCCESS_CODE, 
            {"message": "Scheduler restarted successfully"}
        )
        
    except Exception as e:
        logger.error(f"Error restarting scheduler: {e}")
        return ResponseTemplate.fail("SCHEDULER_RESTART_ERROR", str(e))


@router.post(
    "/force-process/{job_name}",
    summary="특정 Job 강제 처리 API",
    description="특정 Job을 즉시 처리합니다. (디버깅 목적)"
)
async def force_process_job(job_name: str, db: Session = Depends(get_db)):
    """특정 Job을 강제로 처리합니다."""
    try:
        scheduler = get_scheduler()
        
        # 단일 Job 처리 실행
        scheduler._process_single_job(db, job_name)
        
        return ResponseTemplate.success(
            SuccessCode.SUCCESS_CODE,
            {"message": f"Job {job_name} processing triggered"}
        )
        
    except Exception as e:
        logger.error(f"Error force processing job {job_name}: {e}")
        return ResponseTemplate.fail("FORCE_PROCESS_ERROR", str(e))