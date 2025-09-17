from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.repositories.base_repository import BaseRepository
from app.models.sqlite.models.history_models import AnalysisHistoryModel
from app.schemas.analysis import SingleAnalysisResponse, ComparisonAnalysisResponse


class AnalysisHistoryRepository(BaseRepository[AnalysisHistoryModel, Dict[str, Any], Dict[str, Any]]):
    """AI 분석 이력 Repository"""

    def __init__(self):
        super().__init__(AnalysisHistoryModel)

    async def save_single_analysis(
        self,
        db: AsyncSession,
        test_history_id: int,
        analysis_response: SingleAnalysisResponse
    ) -> AnalysisHistoryModel:
        """개별 분석 결과 저장"""

        analysis_record = AnalysisHistoryModel(
            primary_test_id=test_history_id,
            analysis_category="single",
            analysis_type=analysis_response.analysis_type.value,
            analysis_result={
                "summary": analysis_response.summary,
                "detailed_analysis": analysis_response.detailed_analysis,
                "insights": [insight.dict() for insight in analysis_response.insights],
                "performance_score": analysis_response.performance_score,
                "confidence_score": analysis_response.confidence_score
            },
            model_name=analysis_response.model_name,
            analysis_duration_ms=analysis_response.analysis_duration_ms,
            analyzed_at=analysis_response.analyzed_at
        )

        db.add(analysis_record)
        await db.commit()
        await db.refresh(analysis_record)

        return analysis_record

    async def save_comparison_analysis(
        self,
        db: AsyncSession,
        current_test_id: int,
        previous_test_id: int,
        analysis_response: ComparisonAnalysisResponse
    ) -> AnalysisHistoryModel:
        """비교 분석 결과 저장"""

        analysis_record = AnalysisHistoryModel(
            primary_test_id=current_test_id,
            comparison_test_id=previous_test_id,
            analysis_category="comparison",
            analysis_type="comparison",
            analysis_result={
                "comparison_summary": analysis_response.comparison_summary,
                "detailed_comparison": analysis_response.detailed_comparison,
                "improvement_percentage": analysis_response.improvement_percentage,
                "tps_comparison": analysis_response.tps_comparison,
                "response_time_comparison": analysis_response.response_time_comparison,
                "improvements": analysis_response.improvements,
                "regressions": analysis_response.regressions,
                "insights": [insight.dict() for insight in analysis_response.insights] if analysis_response.insights else []
            },
            model_name=analysis_response.model_name,
            analyzed_at=analysis_response.analyzed_at
        )

        db.add(analysis_record)
        await db.commit()
        await db.refresh(analysis_record)

        return analysis_record

    async def get_test_analysis_history(
        self,
        db: AsyncSession,
        test_history_id: int,
        limit: int = 50
    ) -> List[AnalysisHistoryModel]:
        """테스트의 모든 분석 이력 조회 (주 테스트 + 비교 대상으로 사용된 것들)"""

        stmt = select(AnalysisHistoryModel).where(
            (AnalysisHistoryModel.primary_test_id == test_history_id) |
            (AnalysisHistoryModel.comparison_test_id == test_history_id)
        ).order_by(desc(AnalysisHistoryModel.analyzed_at)).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_recent_analyses(
        self,
        db: AsyncSession,
        limit: int = 20
    ) -> List[AnalysisHistoryModel]:
        """최근 분석 이력 조회"""

        stmt = select(AnalysisHistoryModel).order_by(
            desc(AnalysisHistoryModel.analyzed_at)
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_analyses_by_type(
        self,
        db: AsyncSession,
        test_history_id: int,
        analysis_type: str,
        limit: int = 10
    ) -> List[AnalysisHistoryModel]:
        """특정 분석 유형의 이력 조회"""

        stmt = select(AnalysisHistoryModel).where(
            AnalysisHistoryModel.primary_test_id == test_history_id,
            AnalysisHistoryModel.analysis_type == analysis_type
        ).order_by(desc(AnalysisHistoryModel.analyzed_at)).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()


# 싱글톤 인스턴스
_analysis_history_repository: Optional[AnalysisHistoryRepository] = None


def get_analysis_history_repository() -> AnalysisHistoryRepository:
    """AnalysisHistoryRepository 싱글톤 인스턴스 반환"""
    global _analysis_history_repository
    if _analysis_history_repository is None:
        _analysis_history_repository = AnalysisHistoryRepository()
    return _analysis_history_repository