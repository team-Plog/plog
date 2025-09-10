"""
AI 분석용 프롬프트 관리 모듈

부하테스트 결과 분석을 위한 다양한 프롬프트 템플릿을 제공하고,
분석 유형별로 최적화된 프롬프트를 생성합니다.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from app.schemas.analysis import LLMAnalysisInput, AnalysisType


class PromptManager:
    """AI 분석용 프롬프트 관리 클래스"""
    
    def __init__(self):
        self.prompt_templates = {
            AnalysisType.COMPREHENSIVE: self._get_comprehensive_prompt_template(),
            AnalysisType.RESPONSE_TIME: self._get_response_time_prompt_template(),
            AnalysisType.TPS: self._get_tps_prompt_template(),
            AnalysisType.ERROR_RATE: self._get_error_rate_prompt_template(),
            AnalysisType.RESOURCE_USAGE: self._get_resource_usage_prompt_template()
        }
    
    def get_prompt(self, analysis_type: AnalysisType, data: LLMAnalysisInput) -> str:
        """
        분석 유형에 맞는 프롬프트 생성
        
        Args:
            analysis_type: 분석 유형
            data: 분석 데이터
            
        Returns:
            생성된 프롬프트 문자열
        """
        
        template = self.prompt_templates.get(analysis_type)
        if not template:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")
        
        # 데이터를 프롬프트 변수로 변환
        prompt_vars = self._prepare_prompt_variables(data)
        
        # 템플릿에 변수 삽입
        try:
            return template.format(**prompt_vars)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")
    
    def _prepare_prompt_variables(self, data: LLMAnalysisInput) -> Dict[str, Any]:
        """프롬프트 변수 준비"""
        
        # 기본 테스트 정보
        variables = {
            "test_title": data.configuration.title or "Unknown Test",
            "test_duration": data.configuration.test_duration or "N/A",
            "total_requests": data.configuration.total_requests or "N/A",
            "failed_requests": data.configuration.failed_requests or 0,
            "target_tps": data.configuration.target_tps or "N/A",
            "tested_at": data.tested_at.strftime("%Y-%m-%d %H:%M:%S") if data.tested_at else "N/A",
            "is_completed": "완료" if data.is_completed else "진행 중"
        }
        
        # 전체 성능 메트릭
        if data.overall_tps:
            variables.update({
                "overall_tps_avg": data.overall_tps.avg_value or "N/A",
                "overall_tps_max": data.overall_tps.max_value or "N/A",
                "overall_tps_min": data.overall_tps.min_value or "N/A"
            })
        else:
            variables.update({
                "overall_tps_avg": "N/A",
                "overall_tps_max": "N/A", 
                "overall_tps_min": "N/A"
            })
        
        if data.overall_response_time:
            variables.update({
                "overall_rt_avg": data.overall_response_time.avg_value or "N/A",
                "overall_rt_max": data.overall_response_time.max_value or "N/A",
                "overall_rt_min": data.overall_response_time.min_value or "N/A",
                "overall_rt_p50": data.overall_response_time.p50 or "N/A",
                "overall_rt_p95": data.overall_response_time.p95 or "N/A",
                "overall_rt_p99": data.overall_response_time.p99 or "N/A"
            })
        else:
            variables.update({
                "overall_rt_avg": "N/A", "overall_rt_max": "N/A", "overall_rt_min": "N/A",
                "overall_rt_p50": "N/A", "overall_rt_p95": "N/A", "overall_rt_p99": "N/A"
            })
        
        # 에러율 계산
        if data.configuration.total_requests and data.configuration.failed_requests:
            error_rate = (data.configuration.failed_requests / data.configuration.total_requests) * 100
            variables["error_rate"] = f"{error_rate:.2f}%"
        else:
            variables["error_rate"] = "N/A"
        
        # 시나리오 정보
        scenario_count = len(data.scenarios)
        variables["scenario_count"] = scenario_count
        
        scenario_details = []
        for i, scenario in enumerate(data.scenarios[:5], 1):  # 최대 5개까지만 표시
            scenario_info = {
                "name": scenario.scenario_name,
                "executor": scenario.executor,
                "total_requests": scenario.total_requests or "N/A",
                "failed_requests": scenario.failed_requests or 0,
                "think_time": scenario.think_time,
                "endpoint_method": scenario.endpoint.method if scenario.endpoint else "N/A",
                "endpoint_path": scenario.endpoint.path if scenario.endpoint else "N/A"
            }
            scenario_details.append(f"{i}. {scenario_info['name']}: {scenario_info['endpoint_method']} {scenario_info['endpoint_path']}")
        
        variables["scenario_details"] = "\n".join(scenario_details) if scenario_details else "시나리오 정보 없음"
        
        # 리소스 사용량 정보
        if data.resource_usage:
            resource_count = len(data.resource_usage)
            variables["resource_count"] = resource_count
            
            resource_details = []
            for resource in data.resource_usage[:3]:  # 최대 3개까지만 표시
                resource_info = f"- {resource.pod_name} ({resource.service_type}): "
                if resource.avg_cpu_percent is not None:
                    resource_info += f"CPU {resource.avg_cpu_percent:.1f}% (최대 {resource.max_cpu_percent:.1f}%), "
                if resource.avg_memory_percent is not None:
                    resource_info += f"Memory {resource.avg_memory_percent:.1f}% (최대 {resource.max_memory_percent:.1f}%)"
                resource_details.append(resource_info)
            
            variables["resource_details"] = "\n".join(resource_details) if resource_details else "리소스 사용량 정보 없음"
        else:
            variables["resource_count"] = 0
            variables["resource_details"] = "리소스 사용량 정보 없음"
        
        return variables
    
    def _get_comprehensive_prompt_template(self) -> str:
        """종합 분석 프롬프트 템플릿"""
        
        return """다음 부하테스트 결과를 종합적으로 분석해주세요.

=== 테스트 기본 정보 ===
- 테스트명: {test_title}
- 실행 시간: {tested_at}
- 테스트 상태: {is_completed}
- 총 요청 수: {total_requests}
- 실패 요청 수: {failed_requests}
- 목표 TPS: {target_tps}
- 테스트 지속 시간: {test_duration}초

=== 전체 성능 메트릭 ===
- TPS: 평균 {overall_tps_avg}, 최대 {overall_tps_max}, 최소 {overall_tps_min}
- 응답시간: 평균 {overall_rt_avg}ms, P50 {overall_rt_p50}ms, P95 {overall_rt_p95}ms, P99 {overall_rt_p99}ms
- 에러율: {error_rate}

=== 시나리오 정보 ({scenario_count}개) ===
{scenario_details}

=== 리소스 사용량 ({resource_count}개 서버) ===
{resource_details}

다음 형식으로 종합 분석해주세요:

1. **전반적 성능 평가** (3-4문장으로 요약)

2. **주요 발견사항**
   - 성능상 강점 (2-3개)
   - 개선이 필요한 영역 (2-3개)

3. **세부 분석**
   - TPS 성능: 목표 대비 달성도 및 안정성
   - 응답시간: 분포 특성 및 지연 요인
   - 에러 상황: 실패 패턴 및 원인
   - 리소스 효율성: CPU/Memory 사용 패턴

4. **성능 점수** (0-100점, 구체적 근거 포함)

5. **권장사항** (우선순위별 3-5개)

구체적인 수치를 인용하여 객관적으로 분석해주세요."""

    def _get_response_time_prompt_template(self) -> str:
        """응답시간 분석 프롬프트 템플릿"""
        
        return """다음 부하테스트의 응답시간 성능을 상세 분석해주세요.

=== 응답시간 메트릭 ===
- 평균: {overall_rt_avg}ms
- 최대: {overall_rt_max}ms 
- 최소: {overall_rt_min}ms
- P50: {overall_rt_p50}ms
- P95: {overall_rt_p95}ms  
- P99: {overall_rt_p99}ms

=== 테스트 조건 ===
- 총 요청 수: {total_requests}
- 평균 TPS: {overall_tps_avg}
- 테스트 지속 시간: {test_duration}초
- 시나리오 수: {scenario_count}개

=== 시나리오별 세부사항 ===
{scenario_details}

다음 관점에서 응답시간을 분석해주세요:

1. **응답시간 분포 특성**
   - 평균 vs 백분위수 비교 분석
   - 응답시간 일관성 평가
   - 지연 spike 여부

2. **성능 기준 평가**
   - 일반적 웹 서비스 기준 대비 평가
   - SLA 관점에서의 적합성
   - 사용자 경험 영향도

3. **병목 지점 분석**
   - P95, P99가 높은 원인 추정
   - 시나리오별 응답시간 차이
   - 부하 증가에 따른 응답시간 변화

4. **개선 방안**
   - 응답시간 개선을 위한 구체적 권장사항
   - 모니터링해야 할 핵심 지표
   - 성능 목표 설정 제안

수치 기반의 구체적 분석을 해주세요."""

    def _get_tps_prompt_template(self) -> str:
        """TPS 분석 프롬프트 템플릿"""
        
        return """다음 부하테스트의 TPS(처리량) 성능을 상세 분석해주세요.

=== TPS 메트릭 ===
- 평균: {overall_tps_avg}
- 최대: {overall_tps_max}
- 최소: {overall_tps_min}
- 목표: {target_tps}

=== 테스트 조건 ===
- 총 요청 수: {total_requests}
- 테스트 지속 시간: {test_duration}초
- 시나리오 수: {scenario_count}개
- 평균 응답시간: {overall_rt_avg}ms

=== 시나리오 정보 ===
{scenario_details}

다음 관점에서 TPS 성능을 분석해주세요:

1. **처리량 성능 평가**
   - 목표 TPS 달성 여부 및 달성률
   - TPS 안정성 (최대/최소 편차)
   - 전체 테스트 기간 동안의 TPS 일관성

2. **확장성 분석**
   - 현재 TPS에서의 시스템 여유도
   - 추가 부하 처리 가능성 추정
   - 응답시간과 TPS의 상관관계

3. **병목 요인**
   - TPS 제한 요인 추정 (DB, CPU, 네트워크 등)
   - 시나리오별 TPS 차이점
   - 리소스 사용량과의 연관성

4. **성능 개선 방안**
   - TPS 향상을 위한 구체적 권장사항
   - 시스템 튜닝 포인트
   - 인프라 확장 방향성

목표 대비 달성도와 구체적 개선안을 포함해주세요."""

    def _get_error_rate_prompt_template(self) -> str:
        """에러율 분석 프롬프트 템플릿"""
        
        return """다음 부하테스트의 에러율 및 안정성을 상세 분석해주세요.

=== 에러 메트릭 ===
- 총 요청 수: {total_requests}
- 실패 요청 수: {failed_requests}
- 에러율: {error_rate}
- 평균 TPS: {overall_tps_avg}
- 평균 응답시간: {overall_rt_avg}ms

=== 테스트 조건 ===
- 테스트 지속 시간: {test_duration}초
- 시나리오 수: {scenario_count}개

=== 시나리오별 정보 ===
{scenario_details}

다음 관점에서 에러율과 안정성을 분석해주세요:

1. **에러율 평가**
   - 현재 에러율의 심각도 수준
   - 서비스 품질 기준 대비 평가
   - 사용자 경험에 미치는 영향

2. **에러 패턴 분석**
   - 에러 발생 시점 추정 (초기/중반/후반)
   - 부하 증가와 에러율 상관관계
   - 시나리오별 에러 발생 차이

3. **안정성 진단**
   - 시스템 안정성 수준 평가
   - 부하 임계점 분석
   - 장애 전조 증상 여부

4. **에러 원인 추정**
   - 가능한 에러 원인 (타임아웃, 리소스 부족, DB 병목 등)
   - 시스템 컴포넌트별 취약점
   - 네트워크/인프라 관련 이슈

5. **안정성 개선 방안**
   - 에러율 감소를 위한 구체적 조치
   - 모니터링 강화 포인트  
   - 장애 대응 체계 개선안

에러 발생 근본 원인과 예방책을 중심으로 분석해주세요."""

    def _get_resource_usage_prompt_template(self) -> str:
        """리소스 사용량 분석 프롬프트 템플릿"""
        
        return """다음 부하테스트 시 시스템의 리소스 사용량을 상세 분석해주세요.

=== 성능 지표 ===
- 평균 TPS: {overall_tps_avg}
- 평균 응답시간: {overall_rt_avg}ms
- 테스트 지속 시간: {test_duration}초
- 총 요청 수: {total_requests}

=== 리소스 사용량 ({resource_count}개 서버) ===
{resource_details}

다음 관점에서 리소스 효율성을 분석해주세요:

1. **리소스 사용 패턴**
   - CPU/Memory 사용률 수준 평가
   - 리소스 사용의 균형성 (CPU vs Memory)
   - 서버별 리소스 사용 차이

2. **성능 대비 효율성**
   - TPS당 리소스 소모량
   - 응답시간과 리소스 사용량 상관관계
   - 리소스 효율성 점수

3. **확장성 분석**
   - 현재 리소스 여유도
   - 추가 부하 처리 가능 용량
   - 리소스 병목 지점 예측

4. **최적화 기회**
   - 과다/과소 사용 리소스 식별
   - 리소스 배분 최적화 방안
   - 인프라 비용 효율성 개선

5. **용량 계획**
   - 목표 성능 달성을 위한 리소스 요구사항
   - 스케일링 전략 (수직/수평)
   - 리소스 모니터링 권장사항

구체적인 수치를 바탕으로 리소스 최적화 방안을 제시해주세요."""


def get_prompt_manager() -> PromptManager:
    """PromptManager 인스턴스 반환 (싱글톤)"""
    
    if not hasattr(get_prompt_manager, "_instance"):
        get_prompt_manager._instance = PromptManager()
    
    return get_prompt_manager._instance