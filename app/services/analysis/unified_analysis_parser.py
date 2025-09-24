"""
통합 AI 분석 응답 파싱 및 처리 모듈

AI로부터 받은 JSON 형식의 통합 분석 응답을 파싱하여
기존 SingleAnalysisResponse 형식으로 변환합니다.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

from app.schemas.analysis import (
    SingleAnalysisResponse, AnalysisType, AnalysisInsight
)

logger = logging.getLogger(__name__)


class UnifiedAnalysisParser:
    """통합 AI 분석 응답 파싱 클래스"""

    def __init__(self):
        self.analysis_type_mapping = {
            "comprehensive": AnalysisType.COMPREHENSIVE,
            "response_time": AnalysisType.RESPONSE_TIME,
            "tps": AnalysisType.TPS,
            "error_rate": AnalysisType.ERROR_RATE,
            "resource_usage": AnalysisType.RESOURCE_USAGE
        }

    def parse_unified_response(
        self,
        ai_response: str,
        model_name: str,
        analyzed_at: datetime = None
    ) -> List[SingleAnalysisResponse]:
        """
        통합 AI 응답을 파싱하여 SingleAnalysisResponse 리스트로 변환

        Args:
            ai_response: AI로부터 받은 JSON 형식 응답
            model_name: 사용된 AI 모델명
            analyzed_at: 분석 수행 시각

        Returns:
            SingleAnalysisResponse 리스트 (5개)
        """
        if analyzed_at is None:
            analyzed_at = datetime.now()

        try:
            # JSON 추출 및 파싱
            json_data = self._extract_json_from_response(ai_response)

            if not json_data:
                logger.error("Could not extract valid JSON from AI response")
                return self._create_fallback_responses(model_name, analyzed_at)

            # 각 분석 영역별로 SingleAnalysisResponse 생성
            responses = []

            for key, analysis_type in self.analysis_type_mapping.items():
                try:
                    if key in json_data:
                        response = self._parse_single_analysis(
                            json_data[key], analysis_type, model_name, analyzed_at
                        )
                        responses.append(response)
                    else:
                        logger.warning(f"Missing analysis section: {key}")
                        responses.append(
                            self._create_fallback_analysis(analysis_type, model_name, analyzed_at)
                        )
                except Exception as e:
                    logger.error(f"Error parsing {key} analysis: {e}")
                    responses.append(
                        self._create_fallback_analysis(analysis_type, model_name, analyzed_at)
                    )

            logger.info(f"Successfully parsed {len(responses)} analysis responses")
            return responses

        except Exception as e:
            logger.error(f"Error parsing unified response: {e}")
            return self._create_fallback_responses(model_name, analyzed_at)

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """AI 응답에서 JSON 부분을 추출하여 파싱"""

        try:
            # JSON 코드 블록 찾기 (```json...``` 형태)
            json_pattern = r'```json\s*\n(.*?)\n```'
            json_match = re.search(json_pattern, response, re.DOTALL)

            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # 코드 블록이 없다면 중괄호로 시작하는 JSON 찾기
                json_pattern = r'\{.*\}'
                json_match = re.search(json_pattern, response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0).strip()
                else:
                    logger.error("No JSON pattern found in AI response")
                    return None

            # JSON 파싱
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return None

    def _parse_single_analysis(
        self,
        analysis_data: Dict[str, Any],
        analysis_type: AnalysisType,
        model_name: str,
        analyzed_at: datetime
    ) -> SingleAnalysisResponse:
        """개별 분석 데이터를 SingleAnalysisResponse로 변환"""

        # 기본값 설정
        summary = analysis_data.get("summary", f"{analysis_type.value} 분석 요약이 없습니다.")
        detailed_analysis = analysis_data.get("detailed_analysis", "상세 분석 내용이 없습니다.")
        performance_score = analysis_data.get("performance_score")

        # insights 파싱
        insights = []
        raw_insights = analysis_data.get("insights", [])

        for insight_data in raw_insights:
            if isinstance(insight_data, dict):
                insight = AnalysisInsight(
                    category=insight_data.get("category", "performance"),
                    message=insight_data.get("message", "인사이트 메시지가 없습니다."),
                    severity=insight_data.get("severity", "info"),
                    recommendation=insight_data.get("recommendation")
                )
                insights.append(insight)

        # performance_score 검증 및 변환
        if performance_score is not None:
            try:
                performance_score = float(performance_score)
                if not (0 <= performance_score <= 100):
                    logger.warning(f"Performance score {performance_score} out of range, setting to None")
                    performance_score = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid performance score: {performance_score}")
                performance_score = None

        return SingleAnalysisResponse(
            analysis_type=analysis_type,
            summary=summary,
            detailed_analysis=detailed_analysis,
            insights=insights,
            performance_score=performance_score,
            analyzed_at=analyzed_at,
            model_name=model_name
        )

    def _create_fallback_responses(
        self,
        model_name: str,
        analyzed_at: datetime
    ) -> List[SingleAnalysisResponse]:
        """파싱 실패 시 대체 응답 생성"""

        responses = []
        for analysis_type in self.analysis_type_mapping.values():
            response = self._create_fallback_analysis(analysis_type, model_name, analyzed_at)
            responses.append(response)

        return responses

    def _create_fallback_analysis(
        self,
        analysis_type: AnalysisType,
        model_name: str,
        analyzed_at: datetime
    ) -> SingleAnalysisResponse:
        """개별 분석 실패 시 대체 응답 생성"""

        return SingleAnalysisResponse(
            analysis_type=analysis_type,
            summary=f"{analysis_type.value} 분석을 수행할 수 없었습니다.",
            detailed_analysis=f"AI 응답 파싱 중 오류가 발생하여 {analysis_type.value} 분석 결과를 생성할 수 없었습니다.",
            insights=[AnalysisInsight(
                category="system",
                message="분석 응답 파싱 오류로 인해 이 항목은 분석되지 않았습니다.",
                severity="warning"
            )],
            performance_score=None,
            analyzed_at=analyzed_at,
            model_name=model_name
        )


def get_unified_analysis_parser() -> UnifiedAnalysisParser:
    """UnifiedAnalysisParser 인스턴스 반환 (싱글톤)"""

    if not hasattr(get_unified_analysis_parser, "_instance"):
        get_unified_analysis_parser._instance = UnifiedAnalysisParser()

    return get_unified_analysis_parser._instance