import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.schemas.analysis import (
    LLMAnalysisInput, convert_test_history_to_llm_input,
    AnalysisType, SingleAnalysisResponse, ComprehensiveAnalysisResponse,
    AnalysisInsight, AnalysisResult
)
from .prompt_manager import PromptManager
from .ollama_client import get_ollama_client, OllamaConfig
from .unified_analysis_parser import get_unified_analysis_parser
from .timeseries_data_processor import get_timeseries_data_processor
from app.services.testing.test_history_service import (
    get_test_history_by_id, build_test_history_detail_response,
    build_test_history_timeseries_resources_response
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """AI 기반 부하테스트 결과 분석 서비스"""

    def __init__(self):
        self.prompt_manager = PromptManager()
    
    async def perform_single_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int,
        analysis_type: AnalysisType
    ) -> SingleAnalysisResponse:
        """개별 분석 수행"""
        start_time = datetime.now()

        try:
            logger.info(f"Starting {analysis_type.value} analysis for test_history_id: {test_history_id}")

            # 1. 테스트 데이터 수집
            llm_input_data = await self._collect_test_data(db_sync, db_async, test_history_id)

            # 2. AI 설정 로드 및 검증
            if not settings.validate_ai_config():
                raise Exception("Invalid AI configuration. Please check environment variables.")
            ai_config = settings.get_ai_config()

            # 3. Ollama 클라이언트 설정
            ollama_client = await self._setup_ollama_client(ai_config)

            # 4. 분석 실행
            analysis_result = await self._perform_analysis_with_model(
                llm_input_data, analysis_type, ollama_client
            )

            # 5. 응답 구성
            response = SingleAnalysisResponse(
                analysis_type=analysis_type,
                summary=analysis_result.summary,
                detailed_analysis=analysis_result.detailed_analysis,
                insights=analysis_result.insights,
                performance_score=analysis_result.performance_score,
                analyzed_at=datetime.now(),
                model_name=ai_config['model_name']
            )

            # 6. 분석 결과 이력 저장
            await self._save_analysis_history(db_async, test_history_id, response)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Analysis completed in {duration_ms}ms using {ai_config['model_name']}")
            return response

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Single analysis failed for test_history_id {test_history_id} after {duration_ms}ms: {e}")
            raise

    async def perform_comprehensive_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int,
        analysis_types: List[AnalysisType] = None,
    ) -> ComprehensiveAnalysisResponse:
        """
        종합 분석 수행

        Args:
            db_sync: 동기 데이터베이스 세션
            db_async: 비동기 데이터베이스 세션
            test_history_id: 분석할 테스트 히스토리 ID
            analysis_types: 수행할 분석 유형 목록 (기본값: 전체)

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

            # 3. 추세 분석 (제거됨 - 비교 분석 기능 제거)
            trend_analysis = None

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
                trend_analysis=trend_analysis
            )

        except Exception as e:
            logger.error(f"Comprehensive analysis failed for test_history_id {test_history_id}: {e}")
            raise

    async def perform_unified_comprehensive_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int,
    ) -> ComprehensiveAnalysisResponse:
        """
        통합 AI 분석 수행 (새로운 방식)

        5개 영역을 하나의 AI 호출로 처리하며, 시계열 데이터를 포함한
        상관관계 기반 분석을 수행합니다.

        Args:
            db_sync: 동기 데이터베이스 세션
            db_async: 비동기 데이터베이스 세션
            test_history_id: 분석할 테스트 히스토리 ID

        Returns:
            종합 분석 결과
        """
        start_time = datetime.now()

        logger.info(f"Starting unified comprehensive analysis for test_history_id: {test_history_id}")

        try:
            # 1. 테스트 데이터 수집 (시계열 데이터 포함)
            llm_input_data = await self._collect_unified_test_data(db_sync, db_async, test_history_id)

            # 2. AI 설정 로드 및 검증
            if not settings.validate_ai_config():
                raise Exception("Invalid AI configuration. Please check environment variables.")
            ai_config = settings.get_ai_config()

            # 3. Ollama 클라이언트 설정
            ollama_client = await self._setup_ollama_client(ai_config)

            # 4. 통합 분석 실행
            analyses = await self._perform_unified_analysis_with_model(
                llm_input_data, ollama_client, ai_config['model_name']
            )

            # 5. 분석 결과 이력 저장 (각각 개별 저장)
            for analysis in analyses:
                await self._save_analysis_history(db_async, test_history_id, analysis)

            # 6. 종합 분석 결과 계산
            overall_score = self._calculate_overall_score(analyses)
            executive_summary = self._generate_executive_summary(analyses)
            top_recommendations = self._extract_top_recommendations(analyses)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.info(f"Unified comprehensive analysis completed in {duration_ms}ms using {ai_config['model_name']}")

            return ComprehensiveAnalysisResponse(
                test_history_id=test_history_id,
                analyzed_at=datetime.now(),
                model_name=ai_config['model_name'],
                overall_performance_score=overall_score,
                executive_summary=executive_summary,
                analyses=analyses,
                top_recommendations=top_recommendations,
                trend_analysis=None
            )

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Unified comprehensive analysis failed for test_history_id {test_history_id} after {duration_ms}ms: {e}")
            raise

    async def _collect_unified_test_data(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int
    ) -> LLMAnalysisInput:
        """시계열 데이터를 포함한 테스트 데이터 수집"""

        # 기본 테스트 데이터 수집
        llm_input_data = await self._collect_test_data(db_sync, db_async, test_history_id)

        # k6 시계열 데이터 수집 및 전처리
        try:
            from app.services.monitoring.influxdb_service import InfluxDBService

            # 실제 job_name 조회 (test_history에서 가져오기)
            test_history = get_test_history_by_id(db_sync, test_history_id)
            if not test_history or not test_history.job_name:
                raise Exception(f"Test history or job_name not found for test_history_id: {test_history_id}")

            # InfluxDB에서 k6 시계열 데이터 조회
            influxdb_service = InfluxDBService()
            job_name = test_history.job_name  # 실제 job_name 사용
            k6_timeseries_data = influxdb_service.get_test_timeseries_data(job_name)

            if k6_timeseries_data:
                # 시계열 데이터 전처리 (노이즈 제거)
                processor = get_timeseries_data_processor()
                processed_k6_data, k6_context = processor.process_k6_timeseries(k6_timeseries_data)

                logger.info(f"Processed k6 timeseries: {len(processed_k6_data)} points for unified analysis")

                # LLMAnalysisInput에 시계열 데이터 정보 추가
                # (현재 스키마에 직접 필드가 없으므로 메타데이터로 저장)
                llm_input_data.k6_timeseries_data = processed_k6_data
                llm_input_data.k6_analysis_context = k6_context
            else:
                logger.warning(f"No k6 timeseries data found for job: {job_name}")
                llm_input_data.k6_timeseries_data = []
                llm_input_data.k6_analysis_context = "k6 시계열 데이터를 찾을 수 없습니다."

        except Exception as e:
            logger.error(f"Error collecting k6 timeseries data: {e}")
            llm_input_data.k6_timeseries_data = []
            llm_input_data.k6_analysis_context = f"k6 시계열 데이터 수집 중 오류 발생: {str(e)}"

        # 리소스 시계열 데이터 전처리
        if hasattr(llm_input_data, 'resource_usage') and llm_input_data.resource_usage:
            try:
                processor = get_timeseries_data_processor()

                # 리소스 데이터를 적절한 형식으로 변환
                resource_data_for_processing = []
                for resource in llm_input_data.resource_usage:
                    if hasattr(resource, 'usage_data') and resource.usage_data:
                        usage_points = []
                        for point in resource.usage_data:
                            usage_points.append({
                                'timestamp': point.timestamp.isoformat() if hasattr(point.timestamp, 'isoformat') else str(point.timestamp),
                                'usage': {
                                    'cpu_percent': point.cpu_usage_percent,
                                    'memory_percent': point.memory_usage_percent
                                },
                                'actual_usage': {
                                    'cpu_millicores': point.cpu_usage_millicores,
                                    'memory_mb': point.memory_usage_mb
                                }
                            })

                        resource_data_for_processing.append({
                            'pod_name': resource.pod_name,
                            'service_type': resource.service_type,
                            'resource_data': usage_points
                        })

                # 리소스 데이터 전처리
                processed_resource_data, resource_context = processor.process_resource_timeseries(resource_data_for_processing)
                llm_input_data.processed_resource_context = resource_context

                logger.info(f"Processed resource timeseries: {len(processed_resource_data)} pods for unified analysis")

            except Exception as e:
                logger.error(f"Error processing resource timeseries data: {e}")
                llm_input_data.processed_resource_context = f"리소스 시계열 데이터 처리 중 오류 발생: {str(e)}"

        return llm_input_data

    async def _perform_unified_analysis_with_model(
        self,
        data: LLMAnalysisInput,
        ollama_client,
        model_name: str
    ) -> List[SingleAnalysisResponse]:
        """통합 모델 분석 수행"""

        try:
            # 1. 통합 프롬프트 생성
            unified_prompt = self.prompt_manager.get_unified_analysis_prompt(data)

            # 2. 성능 병목 탐지 결과 추가
            bottleneck_context = await self._detect_performance_bottlenecks(data)
            if bottleneck_context:
                unified_prompt = f"{unified_prompt}\n\n**자동 탐지된 성능 병목점:**\n{bottleneck_context}"

            # 3. Ollama API 호출 (통합 분석)
            result = await ollama_client.analyze_performance(unified_prompt, "unified_comprehensive")

            if not result["success"]:
                raise Exception(f"Unified model analysis failed: {result.get('error', 'Unknown error')}")

            # 4. JSON 응답 파싱
            parser = get_unified_analysis_parser()
            analyses = parser.parse_unified_response(
                result["response"],
                model_name,
                datetime.now()
            )

            logger.info(f"Successfully parsed unified analysis into {len(analyses)} individual analyses")
            return analyses

        except Exception as e:
            logger.error(f"Error in unified analysis: {e}")
            # 실패 시 기본 분석 결과 생성
            return self._create_unified_fallback_analyses(model_name)

    def _create_unified_fallback_analyses(self, model_name: str) -> List[SingleAnalysisResponse]:
        """통합 분석 실패 시 대체 분석 결과 생성"""

        analysis_types = [
            AnalysisType.COMPREHENSIVE,
            AnalysisType.RESPONSE_TIME,
            AnalysisType.TPS,
            AnalysisType.ERROR_RATE,
            AnalysisType.RESOURCE_USAGE
        ]

        fallback_analyses = []
        analyzed_at = datetime.now()

        for analysis_type in analysis_types:
            fallback = SingleAnalysisResponse(
                analysis_type=analysis_type,
                summary=f"통합 {analysis_type.value} 분석을 수행할 수 없었습니다.",
                detailed_analysis=f"AI 응답 파싱 오류 또는 모델 분석 실패로 인해 {analysis_type.value} 분석 결과를 생성할 수 없었습니다.",
                insights=[AnalysisInsight(
                    category="system",
                    message="통합 분석 시스템 오류로 인해 이 항목은 분석되지 않았습니다.",
                    severity="warning"
                )],
                performance_score=None,
                analyzed_at=analyzed_at,
                model_name=model_name
            )
            fallback_analyses.append(fallback)

        return fallback_analyses

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

        # 테스트 상세 정보 구성
        test_detail = build_test_history_detail_response(test_history)
        test_detail_dict = test_detail.dict()

        # 리소스 사용량 데이터 조회
        resource_usage_data = None
        try:
            resource_usage_data = await build_test_history_timeseries_resources_response(db_async, test_history_id)
            if resource_usage_data and isinstance(resource_usage_data, list):
                logger.debug(f"Resource usage data collected: {len(resource_usage_data)} servers")
        except Exception as e:
            logger.warning(f"Failed to get resource usage data: {e}")

        return convert_test_history_to_llm_input(test_detail_dict, resource_usage_data)

    async def _setup_ollama_client(self, ai_config: dict):
        """Ollama 클라이언트 설정"""
        config = OllamaConfig.from_settings()
        ollama_client = await get_ollama_client(config)

        if not await ollama_client.is_available():
            raise Exception("Ollama server is not available")

        return ollama_client

    async def _save_analysis_history(self, db_async: AsyncSession, test_history_id: int, response: SingleAnalysisResponse):
        """분석 결과 이력 저장"""
        try:
            from app.repositories.analysis_history_repository import get_analysis_history_repository
            history_repo = get_analysis_history_repository()
            await history_repo.save_single_analysis(db_async, test_history_id, response)
            logger.debug(f"Analysis result saved to history for test_history_id: {test_history_id}")
        except Exception as e:
            logger.warning(f"Failed to save analysis history: {e}")
            # 이력 저장 실패해도 분석 결과는 반환

    async def _detect_performance_bottlenecks(self, data: LLMAnalysisInput) -> str:
        """
        성능 병목 자동 탐지 및 컨텍스트 생성

        Args:
            data: LLM 분석 입력 데이터

        Returns:
            AI 프롬프트에 추가할 병목 분석 컨텍스트 (빈 문자열이면 병목 없음)
        """
        try:
            # InfluxDB에서 시계열 데이터 가져오기
            from app.services.monitoring.influxdb_service import InfluxDBService
            from app.services.analysis.performance_bottleneck_detector import get_performance_bottleneck_detector

            # test_history_id로부터 job_name 추출 (여기서는 간단히 test_history_id를 사용)
            test_history_id = data.test_history_id

            # InfluxDB 서비스를 통해 시계열 데이터 조회
            influxdb_service = InfluxDBService()

            # job_name은 일반적으로 "test-{test_history_id}" 형식으로 생성됨
            job_name = f"test-{test_history_id}"

            # k6 시계열 데이터 조회
            timeseries_data = influxdb_service.get_test_timeseries_data(job_name)

            if not timeseries_data:
                logger.debug(f"No timeseries data found for job: {job_name}")
                return ""

            logger.debug(f"Retrieved {len(timeseries_data)} timeseries data points for bottleneck analysis")

            # 리소스 사용량 데이터 준비 (이미 data.resource_usage에 있음)
            resource_usage_data = []
            if data.resource_usage:
                for resource in data.resource_usage:
                    # ServerResourceUsage 객체를 딕셔너리 형태로 변환
                    usage_points = []
                    for point in resource.usage_data:
                        usage_points.append({
                            'timestamp': point.timestamp,
                            'cpu_usage_percent': point.cpu_usage_percent,
                            'memory_usage_percent': point.memory_usage_percent,
                            'cpu_usage_millicores': point.cpu_usage_millicores,
                            'memory_usage_mb': point.memory_usage_mb
                        })

                    resource_usage_data.append({
                        'pod_name': resource.pod_name,
                        'service_type': resource.service_type,
                        'usage_data': usage_points
                    })

            # 성능 병목 탐지기 실행
            detector = get_performance_bottleneck_detector()
            detected_problems = detector.detect_all_performance_problems(
                load_test_timeseries=timeseries_data,
                resource_usage_timeseries=resource_usage_data
            )

            if not detected_problems:
                logger.debug("No performance bottlenecks detected")
                return ""

            # AI 분석용 컨텍스트 생성
            bottleneck_context = detector.generate_ai_analysis_context(detected_problems)

            logger.info(f"Detected {len(detected_problems)} performance bottlenecks for AI analysis")

            return bottleneck_context

        except Exception as e:
            logger.error(f"Error during performance bottleneck detection: {e}")
            # 병목 탐지 실패 시에도 기본 분석은 계속 진행
            return ""

    # _get_model_config_by_name 메서드 제거됨 - 더 이상 필요 없음


    async def _perform_analysis_with_model(
        self,
        data: LLMAnalysisInput,
        analysis_type: AnalysisType,
        ollama_client
    ) -> AnalysisResult:
        """모델을 사용한 분석 수행"""
        # 성능 병목 자동 탐지 수행
        bottleneck_context = await self._detect_performance_bottlenecks(data)

        # 기본 프롬프트 생성
        base_prompt = self.prompt_manager.get_prompt(analysis_type, data)

        # 병목 분석 결과를 프롬프트에 추가
        if bottleneck_context:
            prompt = f"{base_prompt}\n\n{bottleneck_context}"
        else:
            prompt = base_prompt

        # Ollama API 호출
        result = await ollama_client.analyze_performance(prompt, analysis_type.value)

        if not result["success"]:
            raise Exception(f"Model analysis failed: {result.get('error', 'Unknown error')}")

        # 응답 파싱 (성능 평가 제거)
        analysis_text = result["response"]
        performance_score = result.get("performance_score")

        return self._parse_analysis_response(analysis_type, analysis_text, performance_score)
    
    def _parse_analysis_response(
        self,
        analysis_type: AnalysisType,
        analysis_text: str,
        performance_score: Optional[float] = None
    ) -> AnalysisResult:
        """AI 응답 파싱 (단순화)"""
        lines = analysis_text.strip().split('\n')

        # 요약 추출 (첫 3줄에서 추출)
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

        return AnalysisResult(
            analysis_type=analysis_type.value,
            summary=summary or "분석 요약이 생성되지 않았습니다.",
            detailed_analysis=analysis_text,
            insights=insights,
            performance_score=performance_score
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
            analyzed_at=datetime.now(),
            model_name="fallback"
        )