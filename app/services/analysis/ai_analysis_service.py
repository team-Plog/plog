import logging
from datetime import datetime
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.schemas.analysis import (
    LLMAnalysisInput, convert_test_history_to_llm_input,
    AnalysisType, SingleAnalysisResponse, ComprehensiveAnalysisResponse,
    AnalysisInsight, UnifiedAnalysisOutput
)
from .prompt_manager import PromptManager
from .ollama_client import get_ollama_client, OllamaConfig
from .analysis_parser import get_analysis_parser
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

    async def perform_comprehensive_analysis(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int,
    ) -> ComprehensiveAnalysisResponse:
        """
        통합 AI 분석 수행

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

        logger.info(f"Starting comprehensive analysis for test_history_id: {test_history_id}")

        try:
            # 1. 테스트 데이터 수집 (시계열 데이터 포함)
            llm_input_data = await self._collect_test_data(db_sync, db_async, test_history_id)

            # 2. AI 설정 로드 및 검증
            if not settings.validate_ai_config():
                raise Exception("Invalid AI configuration. Please check environment variables.")
            ai_config = settings.get_ai_config()

            # 3. Ollama 클라이언트 설정
            ollama_client = await self._setup_ollama_client(ai_config)

            # 4. 통합 분석 실행 (LangChain 적용)
            analyses = await self._perform_analysis_with_langchain(
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

            logger.info(f"Comprehensive analysis completed in {duration_ms}ms using {ai_config['model_name']}")

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
            logger.error(f"Comprehensive analysis failed for test_history_id {test_history_id} after {duration_ms}ms: {e}")
            raise

    async def _perform_analysis_with_langchain(
        self,
        data: LLMAnalysisInput,
        ollama_client,
        model_name: str
    ) -> List[SingleAnalysisResponse]:
        """LangChain JsonOutputParser를 사용한 구조화된 분석 수행"""

        try:
            # LangChain 사용 가능 여부 확인
            if not hasattr(self, '_langchain_available'):
                try:
                    from langchain_core.output_parsers import JsonOutputParser
                    from langchain_core.prompts import PromptTemplate
                    self._langchain_available = True
                    self._json_parser = JsonOutputParser(pydantic_object=UnifiedAnalysisOutput)
                    logger.info("LangChain JsonOutputParser initialized successfully")
                except ImportError:
                    logger.warning("LangChain not available, falling back to legacy parser")
                    self._langchain_available = False

            # LangChain에서 템플릿 변수 오류가 발생하므로 임시로 legacy 방식 사용
            if self._langchain_available:
                 return await self._perform_langchain_analysis(data, ollama_client, model_name)
            else:
                return await self._perform_legacy_analysis(data, ollama_client, model_name)

        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return self._create_fallback_analyses(model_name)

    async def _perform_langchain_analysis(
        self,
        data: LLMAnalysisInput,
        ollama_client,
        model_name: str
    ) -> List[SingleAnalysisResponse]:
        """LangChain을 사용한 구조화된 분석"""

        try:
            from langchain_core.prompts import PromptTemplate

            logger.error("DEBUG: Starting LangChain analysis")

            # 구조화된 프롬프트 생성
            logger.error("DEBUG: Getting format instructions")
            format_instructions = self._json_parser.get_format_instructions()
            logger.error(f"DEBUG: Format instructions: {format_instructions[:200]}...")

            logger.error("DEBUG: Creating prompt template")
            base_template = self.prompt_manager.get_analysis_prompt(data)

            # base_template already contains literal JSON with curly braces.
            # Do NOT pass it through PromptTemplate.format() to avoid KeyError from `{...}` inside JSON.
            formatted_prompt = base_template

            # Append format instructions as plain text
            prompt_text = f"{formatted_prompt}\n\n**JSON 스키마 정보:**\n{format_instructions}"

        except Exception as e:
            logger.error(f"DEBUG: Exception in LangChain setup: {e}")
            raise

        logger.error("DEBUG: Getting bottleneck context")
        # 성능 병목 탐지 결과 추가
        bottleneck_context = await self._detect_performance_bottlenecks(data)
        logger.error(f"DEBUG: Bottleneck context length: {len(bottleneck_context) if bottleneck_context else 0}")

        logger.error("DEBUG: Formatting prompt (skipped PromptTemplate; using plain string)")
        # prompt_text already built above
        logger.error(f"DEBUG: Prompt length: {len(prompt_text)}")

        if bottleneck_context:
            prompt_text = f"{prompt_text}\n\n**자동 탐지된 성능 병목점:**\n{bottleneck_context}"
            logger.error("DEBUG: Added bottleneck context to prompt")

        logger.error("DEBUG: Calling Ollama API")
        # Ollama API 호출
        result = await ollama_client.analyze_performance(prompt_text, "langchain_analysis")
        logger.error(f"DEBUG: Ollama API result success: {result.get('success', False)}")

        if not result["success"]:
            raise Exception(f"AI analysis failed: {result.get('error', 'Unknown error')}")

        # LangChain으로 구조화된 파싱
        try:
            raw_response = result["response"]
            logger.error(f"Raw AI response (for debugging): {raw_response}")  # 전체 응답 로깅

            # JSON 응답 정리 시도
            cleaned_response = self._clean_json_response(raw_response)
            if cleaned_response != raw_response:
                logger.error(f"Applied JSON cleaning. Original: {raw_response[:200]}... Cleaned: {cleaned_response[:200]}...")
            else:
                logger.error("No JSON cleaning needed")

            parsed_output = self._json_parser.parse(cleaned_response)
            return self._convert_langchain_output_to_responses(parsed_output, model_name, datetime.now())
        except Exception as e:
            logger.error(f"LangChain parsing failed: {e}")
            logger.error(f"Raw response causing error: {result['response'][:200]}...")
            try:
                cleaned_response = self._clean_json_response(result["response"])
                logger.error(f"Cleaned response was: {cleaned_response[:200]}...")
            except Exception as clean_error:
                logger.error(f"Cleaning response failed: {clean_error}")
                logger.error("Cleaned response was not available (cleaning failed)")
            return await self._perform_legacy_analysis(data, ollama_client, model_name)

    async def _perform_legacy_analysis(
        self,
        data: LLMAnalysisInput,
        ollama_client,
        model_name: str
    ) -> List[SingleAnalysisResponse]:
        """기존 파서를 사용한 분석 (LangChain 실패 시 fallback)"""

        # 프롬프트 생성
        analysis_prompt = self.prompt_manager.get_analysis_prompt(data)

        # 성능 병목 탐지 결과 추가
        bottleneck_context = await self._detect_performance_bottlenecks(data)
        if bottleneck_context:
            analysis_prompt = f"{analysis_prompt}\n\n**자동 탐지된 성능 병목점:**\n{bottleneck_context}"

        # Ollama API 호출
        result = await ollama_client.analyze_performance(analysis_prompt, "legacy_analysis")

        if not result["success"]:
            raise Exception(f"AI analysis failed: {result.get('error', 'Unknown error')}")

        # 기존 파서 사용
        parser = get_analysis_parser()
        analyses = parser.parse_response(
            result["response"],
            model_name,
            datetime.now()
        )

        return analyses

    def _convert_langchain_output_to_responses(
        self,
        parsed_output: UnifiedAnalysisOutput,
        model_name: str,
        analyzed_at: datetime
    ) -> List[SingleAnalysisResponse]:
        """LangChain 파싱 결과를 SingleAnalysisResponse로 변환"""

        responses = []

        # 각 분석 유형별 변환
        analysis_mapping = {
            'comprehensive': AnalysisType.COMPREHENSIVE,
            'response_time': AnalysisType.RESPONSE_TIME,
            'tps': AnalysisType.TPS,
            'error_rate': AnalysisType.ERROR_RATE,
            'resource_usage': AnalysisType.RESOURCE_USAGE
        }

        for field_name, analysis_type in analysis_mapping.items():
            structured_result = getattr(parsed_output, field_name)

            # StructuredAnalysisInsight를 AnalysisInsight로 변환
            insights = []
            for struct_insight in structured_result.insights:
                insight = AnalysisInsight(
                    category=struct_insight.category,
                    message=struct_insight.message,
                    severity=struct_insight.severity,
                    recommendation=struct_insight.recommendation
                )
                insights.append(insight)

            response = SingleAnalysisResponse(
                analysis_type=analysis_type,
                summary=structured_result.summary,
                detailed_analysis=structured_result.detailed_analysis,
                insights=insights,
                performance_score=structured_result.performance_score,
                analyzed_at=analyzed_at,
                model_name=model_name
            )
            responses.append(response)

        return responses

    def _create_fallback_analyses(self, model_name: str) -> List[SingleAnalysisResponse]:
        """분석 실패 시 대체 분석 결과 생성"""

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
                summary=f"{analysis_type.value} 분석을 수행할 수 없었습니다.",
                detailed_analysis=f"AI 응답 파싱 오류 또는 모델 분석 실패로 인해 {analysis_type.value} 분석 결과를 생성할 수 없었습니다.",
                insights=[AnalysisInsight(
                    category="system",
                    message="분석 시스템 오류로 인해 이 항목은 분석되지 않았습니다.",
                    severity="warning"
                )],
                performance_score=None,
                analyzed_at=analyzed_at,
                model_name=model_name
            )
            fallback_analyses.append(fallback)

        return fallback_analyses

    def _clean_json_response(self, response: str) -> str:
        """AI 응답에서 불완전한 JSON을 정리"""
        import re
        import json

        try:
            # 1. 기본 JSON 파싱 시도
            json.loads(response)
            return response
        except json.JSONDecodeError:
            pass

        # 2. 앞뒤 불필요한 텍스트 제거
        cleaned = response.strip()

        # 3. JSON 블록 추출 시도 (```json ... ``` 또는 { ... })
        json_patterns = [
            r'```json\s*(.*?)\s*```',  # ```json {} ``` 형식
            r'```\s*(.*?)\s*```',      # ``` {} ``` 형식
            r'(\{.*\})',               # { } 형식
        ]

        for pattern in json_patterns:
            match = re.search(pattern, cleaned, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue

        # 4. 부분 JSON 복구 시도
        cleaned = self._fix_partial_json(cleaned)

        return cleaned

    def _fix_partial_json(self, partial_json: str) -> str:
        """부분적으로 손상된 JSON 복구"""
        import re
        try:
            # 불완전한 키-값 쌍 제거
            lines = partial_json.split('\n')
            cleaned_lines = []

            for line in lines:
                line = line.strip()
                # 불완전한 키만 있는 라인 건너뛰기 (예: '"comprehensive"')
                if re.match(r'^\s*"[^"]*"\s*$', line):
                    continue
                cleaned_lines.append(line)

            result = '\n'.join(cleaned_lines)

            # JSON 구조 검증 및 자동 완성
            if result.strip().startswith('{') and not result.strip().endswith('}'):
                result += '}'

            return result

        except Exception:
            return partial_json

    async def _collect_test_data(
        self,
        db_sync: Session,
        db_async: AsyncSession,
        test_history_id: int
    ) -> LLMAnalysisInput:
        """테스트 데이터 수집 (시계열 데이터 포함)"""
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

        # 기본 LLM 입력 데이터 생성
        llm_input_data = convert_test_history_to_llm_input(test_detail_dict, resource_usage_data)

        # k6 시계열 데이터 수집 및 전처리
        try:
            from app.services.monitoring.influxdb_service import InfluxDBService

            if test_history.job_name:
                # InfluxDB에서 k6 시계열 데이터 조회
                influxdb_service = InfluxDBService()
                k6_timeseries_data = influxdb_service.get_test_timeseries_data(test_history.job_name)

                if k6_timeseries_data:
                    # 시계열 데이터 전처리
                    processor = get_timeseries_data_processor()
                    processed_k6_data, k6_context = processor.process_k6_timeseries(k6_timeseries_data)

                    logger.info(f"Processed k6 timeseries: {len(processed_k6_data)} points")

                    # 시계열 데이터 추가
                    llm_input_data.k6_timeseries_data = processed_k6_data
                    llm_input_data.k6_analysis_context = k6_context
                else:
                    logger.warning(f"No k6 timeseries data found for job: {test_history.job_name}")
                    llm_input_data.k6_timeseries_data = []
                    llm_input_data.k6_analysis_context = "k6 시계열 데이터를 찾을 수 없습니다."
            else:
                logger.warning(f"No job_name found for test_history_id: {test_history_id}")
                llm_input_data.k6_timeseries_data = []
                llm_input_data.k6_analysis_context = "job_name이 없어 시계열 데이터를 수집할 수 없습니다."

        except Exception as e:
            logger.error(f"Error collecting k6 timeseries data: {e}")
            llm_input_data.k6_timeseries_data = []
            llm_input_data.k6_analysis_context = f"k6 시계열 데이터 수집 중 오류 발생: {str(e)}"

        # 리소스 시계열 데이터 전처리
        if hasattr(llm_input_data, 'resource_usage') and llm_input_data.resource_usage:
            try:
                processor = get_timeseries_data_processor()

                # 리소스 데이터 변환
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

                logger.info(f"Processed resource timeseries: {len(processed_resource_data)} pods")

            except Exception as e:
                logger.error(f"Error processing resource timeseries data: {e}")
                llm_input_data.processed_resource_context = f"리소스 시계열 데이터 처리 중 오류 발생: {str(e)}"

        return llm_input_data

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