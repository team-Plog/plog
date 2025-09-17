import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.schemas.analysis import (
    LLMAnalysisInput, convert_test_history_to_llm_input,
    AnalysisType, SingleAnalysisResponse, ComprehensiveAnalysisResponse,
    ComparisonAnalysisResponse, AnalysisInsight
)
from .prompt_manager import PromptManager
from .ollama_client import get_ollama_client, OllamaConfig
# 모델 매니저 제거됨 - 간단한 설정 사용
from app.services.testing.test_history_service import (
    get_test_history_by_id, build_test_history_detail_response,
    build_test_history_timeseries_resources_response
)

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """개선된 AI 기반 부하테스트 결과 분석 서비스"""
    
    def __init__(self):
        self.prompt_manager = PromptManager()
    
    async def perform_single_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int,
        analysis_type: AnalysisType
    ) -> SingleAnalysisResponse:
        """
        개별 분석 수행
        
        Args:
            db_sync: 동기 데이터베이스 세션
            db_async: 비동기 데이터베이스 세션
            test_history_id: 분석할 테스트 히스토리 ID
            analysis_type: 분석 유형
            
        Returns:
            개별 분석 결과
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting {analysis_type.value} analysis for test_history_id: {test_history_id}")

            # 1. 실제 테스트 데이터 수집
            logger.debug("Step 1: Collecting actual test data from database")
            from app.schemas.analysis import LLMAnalysisInput
            from app.schemas.analysis.analysis_models import convert_test_history_to_llm_input
            from app.services.testing.test_history_service import build_test_history_detail_response

            # 실제 테스트 데이터 조회
            from app.services.testing.test_history_service import get_test_history_by_id

            test_history = get_test_history_by_id(db_sync, test_history_id)
            if not test_history:
                raise ValueError(f"Test history not found for ID: {test_history_id}")

            test_detail_response = build_test_history_detail_response(test_history)
            test_history_detail = test_detail_response.dict()  # Pydantic 객체를 dict로 변환

            # 리소스 사용량 데이터 수집
            resource_usage_data = None
            try:
                # build_test_history_timeseries_resources_response returns the raw data directly
                resource_usage_data = await build_test_history_timeseries_resources_response(db_async, test_history_id)
                logger.debug(f"Resource usage data type: {type(resource_usage_data)}")
                logger.debug(f"Resource usage data: {resource_usage_data}")

                if resource_usage_data and isinstance(resource_usage_data, list):
                    logger.debug(f"Resource usage data collected: {len(resource_usage_data)} servers")
                    if resource_usage_data:
                        logger.debug(f"First server keys: {resource_usage_data[0].keys()}")
                        if "resource_data" in resource_usage_data[0]:
                            logger.debug(f"First server has {len(resource_usage_data[0]['resource_data'])} resource data points")
                else:
                    logger.warning(f"Resource usage data is empty or invalid: {resource_usage_data}")
                    resource_usage_data = None
            except Exception as e:
                logger.warning(f"Failed to get resource usage data: {e}")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                resource_usage_data = None

            # LLMAnalysisInput으로 변환
            llm_input_data = convert_test_history_to_llm_input(
                test_history_detail=test_history_detail,
                resource_usage_data=resource_usage_data
            )
            logger.debug("Step 1: Real test data collected and converted successfully")
            
            # 2. 모델 설정 (환경변수에서 직접 가져오기)
            logger.debug("Step 2: Setting up model configuration")
            from app.core.config import settings

            # 간단한 모델 설정
            model_config = {
                'model_name': settings.AI_MODEL_NAME,
                'temperature': 0.1,
                'max_tokens': 3000,
                'timeout_seconds': 120
            }
            logger.debug(f"Step 2: Model config created: {model_config}")
            
            # 3. Ollama 클라이언트 설정
            logger.debug("Step 3: Setting up Ollama client")
            ollama_client = await get_ollama_client()
            config = OllamaConfig()
            config.base_url = settings.OLLAMA_HOST  # 환경변수에서 Ollama 호스트 설정
            config.model_name = model_config['model_name']
            config.temperature = model_config['temperature']
            config.max_tokens = model_config['max_tokens']
            config.timeout_seconds = model_config['timeout_seconds']
            ollama_client.config = config
            logger.debug(f"Step 3: Ollama client configured with host: {settings.OLLAMA_HOST}")
            
            if not await ollama_client.is_available():
                raise Exception("Ollama server is not available")
            
            # 4. 분석 실행
            analysis_result = await self._perform_analysis_with_model(
                llm_input_data, analysis_type, ollama_client
            )
            
            # 5. 성능 기록 (간단한 로그)
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Analysis completed in {duration_ms}ms using {model_config['model_name']}")
            
            # 6. 응답 구성
            response = SingleAnalysisResponse(
                analysis_type=analysis_type,
                summary=analysis_result.summary,
                detailed_analysis=analysis_result.detailed_analysis,
                insights=analysis_result.insights,
                performance_score=analysis_result.performance_score,
                confidence_score=analysis_result.confidence_score,
                analyzed_at=datetime.now(),
                model_name=model_config['model_name'],
                analysis_duration_ms=duration_ms
            )

            # 7. 분석 결과 이력 저장
            try:
                from app.repositories.analysis_history_repository import get_analysis_history_repository
                history_repo = get_analysis_history_repository()
                await history_repo.save_single_analysis(db_async, test_history_id, response)
                logger.debug(f"Analysis result saved to history for test_history_id: {test_history_id}")
            except Exception as e:
                logger.warning(f"Failed to save analysis history: {e}")
                # 이력 저장 실패해도 분석 결과는 반환

            return response
            
        except Exception as e:
            # 실패 로그
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Single analysis failed for test_history_id {test_history_id} after {duration_ms}ms: {e}")
            raise
    
    async def perform_comprehensive_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int,
        analysis_types: List[AnalysisType] = None,
        comparison_test_ids: Optional[List[int]] = None
    ) -> ComprehensiveAnalysisResponse:
        """
        종합 분석 수행

        Args:
            db_sync: 동기 데이터베이스 세션
            db_async: 비동기 데이터베이스 세션
            test_history_id: 분석할 테스트 히스토리 ID
            analysis_types: 수행할 분석 유형 목록 (기본값: 전체)
            comparison_test_ids: 비교 분석용 테스트 ID 목록

        Returns:
            종합 분석 결과
        """
        start_time = datetime.now()
        
        # 기본 분석 유형 설정
        if analysis_types is None:
            analysis_types = [
                AnalysisType.COMPREHENSIVE,
                AnalysisType.RESPONSE_TIME,
                AnalysisType.TPS,
                AnalysisType.ERROR_RATE,
                AnalysisType.RESOURCE_USAGE
            ]
        
        logger.info(f"Starting comprehensive analysis for test_history_id: {test_history_id}")
        
        try:
            # 1. 각 분석 유형별 실행
            analyses = []
            for analysis_type in analysis_types:
                try:
                    single_result = await self.perform_single_analysis(
                        db_sync, db_async, test_history_id, analysis_type
                    )
                    analyses.append(single_result)
                    logger.info(f"Completed {analysis_type.value} analysis")
                except Exception as e:
                    logger.error(f"Failed {analysis_type.value} analysis: {e}")
                    # 실패한 분석은 기본값으로 대체
                    analyses.append(self._create_fallback_analysis(analysis_type, str(e)))
            
            # 2. 종합 분석 결과 계산
            overall_score = self._calculate_overall_score(analyses)
            executive_summary = self._generate_executive_summary(analyses)
            top_recommendations = self._extract_top_recommendations(analyses)
            
            # 3. 비교 분석 (선택사항)
            trend_analysis = None
            if comparison_test_ids:
                trend_analysis = await self._perform_trend_analysis(
                    db_sync, db_async, test_history_id, comparison_test_ids
                )
            
            # 4. 사용된 모델명 (첫 번째 성공한 분석의 모델 사용)
            used_model = next(
                (a.model_name for a in analyses if a.model_name != "fallback"),
                "unknown"
            )
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ComprehensiveAnalysisResponse(
                test_history_id=test_history_id,
                analyzed_at=datetime.now(),
                model_name=used_model,
                overall_performance_score=overall_score,
                executive_summary=executive_summary,
                analyses=analyses,
                top_recommendations=top_recommendations,
                trend_analysis=trend_analysis,
                total_analysis_duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Comprehensive analysis failed for test_history_id {test_history_id}: {e}")
            raise
    
    async def perform_comparison_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        current_test_id: int,
        previous_test_id: int,
        focus_areas: Optional[List[str]] = None
    ) -> ComparisonAnalysisResponse:
        """
        비교 분석 수행

        Args:
            db_sync: 동기 데이터베이스 세션
            db_async: 비동기 데이터베이스 세션
            current_test_id: 현재 테스트 ID
            previous_test_id: 이전 테스트 ID
            focus_areas: 집중 분석 영역

        Returns:
            비교 분석 결과
        """
        start_time = datetime.now()
        
        logger.info(f"Starting comparison analysis: {current_test_id} vs {previous_test_id}")
        
        try:
            # 1. 양쪽 테스트 데이터 수집
            current_data = await self._collect_test_data(db_sync, db_async, current_test_id)
            previous_data = await self._collect_test_data(db_sync, db_async, previous_test_id)
            
            # 2. 모델 설정 (환경변수에서 직접 가져오기)
            from app.core.config import settings

            model_config = {
                'model_name': settings.AI_MODEL_NAME,
                'temperature': 0.05,  # 비교 분석은 일관성이 중요
                'max_tokens': 3000,
                'timeout_seconds': 120
            }
            
            # 3. 비교 분석용 프롬프트 생성
            comparison_prompt = self._generate_comparison_prompt(
                current_data, previous_data, focus_areas
            )
            
            # 4. Ollama 클라이언트 설정 및 분석 수행
            ollama_client = await get_ollama_client()
            config = OllamaConfig()
            config.model_name = model_config['model_name']
            config.temperature = model_config['temperature']
            config.max_tokens = model_config['max_tokens']
            config.timeout_seconds = model_config['timeout_seconds']
            ollama_client.config = config
            
            result = await ollama_client.analyze_performance(comparison_prompt, "comparison")
            
            if not result["success"]:
                raise Exception(f"Comparison analysis failed: {result.get('error', 'Unknown error')}")
            
            # 5. 결과 파싱
            comparison_result = self._parse_comparison_response(
                result["response"], current_data, previous_data
            )
            
            # 6. 성능 기록 (간단한 로그)
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Comparison analysis completed in {duration_ms}ms using {model_config['model_name']}")

            response = ComparisonAnalysisResponse(
                current_test_id=current_test_id,
                previous_test_id=previous_test_id,
                analyzed_at=datetime.now(),
                model_name=model_config['model_name'],
                **comparison_result
            )

            # 비교 분석 결과 이력 저장
            try:
                from app.repositories.analysis_history_repository import get_analysis_history_repository
                history_repo = get_analysis_history_repository()
                await history_repo.save_comparison_analysis(db_async, current_test_id, previous_test_id, response)
                logger.debug(f"Comparison analysis result saved to history: {current_test_id} vs {previous_test_id}")
            except Exception as e:
                logger.warning(f"Failed to save comparison analysis history: {e}")
                # 이력 저장 실패해도 분석 결과는 반환

            return response
            
        except Exception as e:
            logger.error(f"Comparison analysis failed: {e}")
            raise
    
    async def _collect_test_data(
        self, 
        db_sync: Session, 
        db_async: AsyncSession, 
        test_history_id: int
    ) -> LLMAnalysisInput:
        """테스트 데이터 수집"""
        
        test_history = get_test_history_by_id(db_sync, test_history_id)
        if not test_history:
            raise Exception(f"Test history not found: {test_history_id}")
        
        # 응답 형식으로 변환
        test_detail = build_test_history_detail_response(test_history)
        test_detail_dict = test_detail.dict()
        
        # 리소스 사용량 데이터 조회
        resource_usage_data = None
        try:
            resource_usage_data = await build_test_history_timeseries_resources_response(db_async, test_history_id)
        except Exception as e:
            logger.warning(f"Failed to get resource usage data: {e}")
        
        return convert_test_history_to_llm_input(test_detail_dict, resource_usage_data)
    
    # _get_model_config_by_name 메서드 제거됨 - 더 이상 필요 없음
    
    def _estimate_data_complexity(self, data: LLMAnalysisInput) -> str:
        """데이터 복잡도 추정"""
        
        complexity_score = 0
        
        # 시나리오 수에 따른 복잡도
        scenario_count = len(data.scenarios)
        if scenario_count > 5:
            complexity_score += 2
        elif scenario_count > 2:
            complexity_score += 1
        
        # 리소스 데이터 존재 여부
        if data.resource_usage:
            complexity_score += 1
            
            # 리소스 데이터 포인트 수
            total_points = sum(len(r.usage_data) for r in data.resource_usage)
            if total_points > 1000:
                complexity_score += 2
            elif total_points > 100:
                complexity_score += 1
        
        # 테스트 지속 시간
        if data.configuration.test_duration and data.configuration.test_duration > 300:  # 5분 이상
            complexity_score += 1
        
        # 복잡도 분류
        if complexity_score >= 4:
            return "high"
        elif complexity_score >= 2:
            return "medium"
        else:
            return "low"
    
    async def _perform_analysis_with_model(
        self,
        data: LLMAnalysisInput,
        analysis_type: AnalysisType,
        ollama_client
    ) -> 'AnalysisResult':
        """모델을 사용한 분석 수행"""
        
        # schemas의 AnalysisResult를 사용
        from app.schemas.analysis import AnalysisResult
        
        # 프롬프트 생성
        prompt = self.prompt_manager.get_prompt(analysis_type, data)
        
        # Ollama API 호출
        result = await ollama_client.analyze_performance(prompt, analysis_type.value)
        
        if not result["success"]:
            raise Exception(f"Model analysis failed: {result.get('error', 'Unknown error')}")
        
        # 응답 파싱
        analysis_text = result["response"]
        performance_score = result.get("performance_score")
        
        return self._parse_analysis_response(analysis_type, analysis_text, performance_score)
    
    def _parse_analysis_response(
        self, 
        analysis_type: AnalysisType, 
        analysis_text: str, 
        performance_score: Optional[float] = None
    ) -> 'AnalysisResult':
        """AI 응답 파싱 (기존 로직 재사용)"""
        
        from app.schemas.analysis import AnalysisResult, AnalysisInsight
        
        lines = analysis_text.strip().split('\n')
        
        # 요약 추출
        summary = ""
        if len(lines) > 0:
            summary_lines = []
            for line in lines[:5]:
                if line.strip() and not line.startswith('#'):
                    summary_lines.append(line.strip())
                    if len(summary_lines) >= 3:
                        break
            summary = ' '.join(summary_lines)
        
        # 인사이트 추출
        insights = self._extract_insights(analysis_text)
        
        # 신뢰도 점수 계산
        confidence_score = self._calculate_confidence_score(analysis_text)
        
        return AnalysisResult(
            analysis_type=analysis_type.value,
            summary=summary or "분석 요약이 생성되지 않았습니다.",
            detailed_analysis=analysis_text,
            insights=insights,
            performance_score=performance_score,
            confidence_score=confidence_score
        )
    
    def _extract_insights(self, analysis_text: str) -> List[AnalysisInsight]:
        """인사이트 추출 (기존 로직)"""
        
        insights = []
        warning_keywords = ["위험", "문제", "병목", "제한", "초과", "높음", "지연"]
        critical_keywords = ["심각", "실패", "오류", "중단", "불안정"]
        optimization_keywords = ["개선", "최적화", "권장", "제안", "향상"]
        
        sentences = analysis_text.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            severity = "info"
            category = "performance"
            
            if any(keyword in sentence for keyword in critical_keywords):
                severity = "critical"
            elif any(keyword in sentence for keyword in warning_keywords):
                severity = "warning"
            
            if any(keyword in sentence for keyword in optimization_keywords):
                category = "optimization"
            elif "리소스" in sentence or "CPU" in sentence or "메모리" in sentence:
                category = "resource"
            elif "에러" in sentence or "오류" in sentence:
                category = "reliability"
            
            if severity in ["warning", "critical"] or category == "optimization":
                insights.append(AnalysisInsight(
                    category=category,
                    message=sentence,
                    severity=severity,
                    recommendation=None
                ))
        
        return insights[:5]
    
    def _calculate_confidence_score(self, analysis_text: str) -> float:
        """신뢰도 점수 계산 (기존 로직)"""
        
        score = 0.5
        text_length = len(analysis_text)
        
        if text_length > 1000:
            score += 0.2
        elif text_length > 500:
            score += 0.1
        
        import re
        numbers_count = len(re.findall(r'\d+(?:\.\d+)?', analysis_text))
        if numbers_count > 10:
            score += 0.1
        elif numbers_count > 5:
            score += 0.05
        
        technical_terms = ["TPS", "응답시간", "CPU", "메모리", "P95", "P99", "에러율"]
        term_count = sum(1 for term in technical_terms if term in analysis_text)
        score += min(term_count * 0.02, 0.1)
        
        if "권장" in analysis_text or "개선" in analysis_text or "최적화" in analysis_text:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_overall_score(self, analyses: List[SingleAnalysisResponse]) -> float:
        """전체 성능 점수 계산"""
        
        scored_analyses = [a for a in analyses if a.performance_score is not None]
        
        if not scored_analyses:
            return 70.0
        
        total_weight = 0
        weighted_sum = 0
        
        for analysis in scored_analyses:
            weight = 2.0 if analysis.analysis_type == AnalysisType.COMPREHENSIVE else 1.0
            weighted_sum += analysis.performance_score * weight
            total_weight += weight
        
        return round(weighted_sum / total_weight, 1) if total_weight > 0 else 70.0
    
    def _generate_executive_summary(self, analyses: List[SingleAnalysisResponse]) -> str:
        """경영진용 요약 생성"""
        
        comprehensive_analysis = next(
            (a for a in analyses if a.analysis_type == AnalysisType.COMPREHENSIVE),
            None
        )
        
        if comprehensive_analysis:
            first_sentence = comprehensive_analysis.summary.split('.')[0].strip()
            if first_sentence:
                return first_sentence + "."
        
        summaries = [a.summary.split('.')[0] for a in analyses if a.summary]
        if summaries:
            return summaries[0] + "."
        
        return "부하테스트 분석이 완료되었습니다."
    
    def _extract_top_recommendations(self, analyses: List[SingleAnalysisResponse]) -> List[str]:
        """상위 권장사항 추출"""
        
        recommendations = []
        
        for analysis in analyses:
            for insight in analysis.insights:
                if insight.category == "optimization" or insight.severity in ["warning", "critical"]:
                    if insight.recommendation:
                        recommendations.append(insight.recommendation)
                    else:
                        if "권장" in insight.message or "개선" in insight.message:
                            recommendations.append(insight.message)
        
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:5]
    
    async def _perform_trend_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        current_test_id: int,
        comparison_test_ids: List[int]
    ) -> Optional[str]:
        """추세 분석"""
        
        try:
            current_test = get_test_history_by_id(db_sync, current_test_id)
            if not current_test:
                return None
            
            comparison_results = []
            
            for test_id in comparison_test_ids:
                prev_test = get_test_history_by_id(db_sync, test_id)
                if prev_test:
                    tps_change = self._calculate_percentage_change(
                        prev_test.avg_tps, current_test.avg_tps
                    )
                    response_time_change = self._calculate_percentage_change(
                        prev_test.avg_response_time, current_test.avg_response_time
                    )
                    error_rate_change = self._calculate_percentage_change(
                        prev_test.avg_error_rate, current_test.avg_error_rate
                    )
                    
                    comparison_results.append({
                        "test_id": test_id,
                        "tps_change": tps_change,
                        "response_time_change": response_time_change,
                        "error_rate_change": error_rate_change
                    })
            
            if comparison_results:
                return self._generate_trend_summary(comparison_results)
            
        except Exception as e:
            logger.warning(f"Trend analysis failed: {e}")
        
        return None
    
    def _calculate_percentage_change(self, old_value: Optional[float], new_value: Optional[float]) -> Optional[float]:
        """퍼센트 변화율 계산"""
        if old_value is None or new_value is None or old_value == 0:
            return None
        
        return round(((new_value - old_value) / old_value) * 100, 1)
    
    def _generate_trend_summary(self, comparison_results: List[Dict[str, Any]]) -> str:
        """추세 요약 생성"""
        
        if not comparison_results:
            return "비교할 이전 테스트 데이터가 없습니다."
        
        avg_tps_change = self._calculate_average_change([r["tps_change"] for r in comparison_results])
        avg_rt_change = self._calculate_average_change([r["response_time_change"] for r in comparison_results])
        avg_error_change = self._calculate_average_change([r["error_rate_change"] for r in comparison_results])
        
        summary_parts = []
        
        if avg_tps_change is not None:
            direction = "향상" if avg_tps_change > 0 else "저하"
            summary_parts.append(f"TPS가 평균 {abs(avg_tps_change):.1f}% {direction}")
        
        if avg_rt_change is not None:
            direction = "증가" if avg_rt_change > 0 else "개선"
            summary_parts.append(f"응답시간이 평균 {abs(avg_rt_change):.1f}% {direction}")
        
        if avg_error_change is not None:
            direction = "증가" if avg_error_change > 0 else "감소"
            summary_parts.append(f"에러율이 평균 {abs(avg_error_change):.1f}% {direction}")
        
        return "이전 테스트 대비 " + ", ".join(summary_parts) + "했습니다."
    
    def _calculate_average_change(self, changes: List[Optional[float]]) -> Optional[float]:
        """변화율 평균 계산"""
        valid_changes = [c for c in changes if c is not None]
        return sum(valid_changes) / len(valid_changes) if valid_changes else None
    
    def _generate_comparison_prompt(
        self,
        current_data: LLMAnalysisInput,
        previous_data: LLMAnalysisInput,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """비교 분석용 프롬프트 생성"""
        
        focus_text = ""
        if focus_areas:
            focus_mapping = {
                "tps": "처리량(TPS)",
                "response_time": "응답시간", 
                "error_rate": "에러율",
                "resource_usage": "리소스 사용량"
            }
            focused_areas = [focus_mapping.get(area, area) for area in focus_areas]
            focus_text = f"\n특히 다음 영역에 집중하여 분석해주세요: {', '.join(focused_areas)}"
        
        prompt = f"""
부하테스트 결과를 비교 분석해주세요.

=== 이전 테스트 결과 ===
- 테스트명: {previous_data.configuration.title}
- 총 요청 수: {previous_data.configuration.total_requests or 'N/A'}
- 실패 요청 수: {previous_data.configuration.failed_requests or 0}
- 테스트 시간: {previous_data.configuration.test_duration or 'N/A'}초
- 평균 TPS: {previous_data.overall_tps.avg_value if previous_data.overall_tps else 'N/A'}
- 평균 응답시간: {previous_data.overall_response_time.avg_value if previous_data.overall_response_time else 'N/A'}ms
- P95 응답시간: {previous_data.overall_response_time.p95 if previous_data.overall_response_time else 'N/A'}ms

=== 현재 테스트 결과 ===
- 테스트명: {current_data.configuration.title}
- 총 요청 수: {current_data.configuration.total_requests or 'N/A'}
- 실패 요청 수: {current_data.configuration.failed_requests or 0}
- 테스트 시간: {current_data.configuration.test_duration or 'N/A'}초
- 평균 TPS: {current_data.overall_tps.avg_value if current_data.overall_tps else 'N/A'}
- 평균 응답시간: {current_data.overall_response_time.avg_value if current_data.overall_response_time else 'N/A'}ms
- P95 응답시간: {current_data.overall_response_time.p95 if current_data.overall_response_time else 'N/A'}ms
{focus_text}

다음 형식으로 비교 분석해주세요:

1. **변화 요약** (2-3문장으로 전반적인 변화 상황 요약)

2. **지표별 상세 비교**
   - TPS 변화: 수치와 변화율, 원인 분석
   - 응답시간 변화: 수치와 변화율, 원인 분석  
   - 에러율 변화: 수치와 변화율, 원인 분석

3. **주요 개선사항** (3개 이내)

4. **성능 저하 사항** (있는 경우, 3개 이내)

5. **종합 평가 및 권장사항**

구체적인 수치와 변화율을 포함하여 객관적으로 분석해주세요.
"""
        return prompt
    
    def _parse_comparison_response(
        self,
        response_text: str,
        current_data: LLMAnalysisInput,
        previous_data: LLMAnalysisInput
    ) -> Dict[str, Any]:
        """비교 분석 응답 파싱"""
        
        # 수치 비교 계산
        tps_comparison = None
        if current_data.overall_tps and previous_data.overall_tps:
            current_tps = current_data.overall_tps.avg_value or 0
            previous_tps = previous_data.overall_tps.avg_value or 0
            change_pct = self._calculate_percentage_change(previous_tps, current_tps) or 0
            
            tps_comparison = {
                "previous": previous_tps,
                "current": current_tps,
                "change_percent": change_pct
            }
        
        response_time_comparison = None
        if current_data.overall_response_time and previous_data.overall_response_time:
            current_rt = current_data.overall_response_time.avg_value or 0
            previous_rt = previous_data.overall_response_time.avg_value or 0
            change_pct = self._calculate_percentage_change(previous_rt, current_rt) or 0
            
            response_time_comparison = {
                "previous": previous_rt,
                "current": current_rt,
                "change_percent": change_pct
            }
        
        # 전반적 개선도 계산
        improvement_percentage = None
        if tps_comparison and response_time_comparison:
            tps_improvement = tps_comparison["change_percent"]
            rt_improvement = -response_time_comparison["change_percent"]  # 응답시간 감소가 개선
            improvement_percentage = (tps_improvement + rt_improvement) / 2
        
        # 텍스트에서 개선사항과 저하사항 추출
        improvements = []
        regressions = []
        
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if "개선" in line and any(word in line for word in ["사항", "점"]):
                current_section = "improvements"
                continue
            elif "저하" in line or "퇴보" in line:
                current_section = "regressions"
                continue
            elif line.startswith(('-', '•', '*')) and current_section:
                item = line.lstrip('-•* ').strip()
                if item:
                    if current_section == "improvements":
                        improvements.append(item)
                    elif current_section == "regressions":
                        regressions.append(item)
        
        # 요약 추출 (첫 번째 단락)
        summary_lines = []
        for line in lines:
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())
                if len(summary_lines) >= 3:
                    break
        
        comparison_summary = ' '.join(summary_lines) if summary_lines else "비교 분석이 완료되었습니다."
        
        # 인사이트 추출
        insights = self._extract_insights(response_text)
        
        return {
            "comparison_summary": comparison_summary,
            "improvement_percentage": improvement_percentage,
            "tps_comparison": tps_comparison,
            "response_time_comparison": response_time_comparison,
            "error_rate_comparison": None,  # TODO: 에러율 비교 구현
            "resource_usage_comparison": None,  # TODO: 리소스 비교 구현
            "improvements": improvements[:3],
            "regressions": regressions[:3],
            "detailed_comparison": response_text,
            "insights": insights
        }
    
    def _create_fallback_analysis(self, analysis_type: AnalysisType, error_message: str) -> SingleAnalysisResponse:
        """분석 실패 시 대체 분석 결과 생성"""
        
        return SingleAnalysisResponse(
            analysis_type=analysis_type,
            summary=f"{analysis_type.value} 분석을 수행할 수 없었습니다.",
            detailed_analysis=f"분석 중 오류가 발생했습니다: {error_message}",
            insights=[AnalysisInsight(
                category="system",
                message="분석 시스템 오류로 인해 이 항목은 분석되지 않았습니다.",
                severity="warning"
            )],
            performance_score=None,
            confidence_score=0.0,
            analyzed_at=datetime.now(),
            model_name="fallback",
            analysis_duration_ms=0
        )