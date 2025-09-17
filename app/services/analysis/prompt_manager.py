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

        return """부하테스트 결과를 분석하여 서비스의 성능과 안정성을 평가해주세요. 반드시 한국어로 응답해주세요.

**테스트 정보**
- 테스트명: {test_title}
- 목표 TPS: {target_tps} | 지속시간: {test_duration}초
- 총 요청: {total_requests}건, 실패: {failed_requests}건

**성능 결과**
- TPS: 평균 {overall_tps_avg} (최소 {overall_tps_min} ~ 최대 {overall_tps_max})
- 응답시간: 평균 {overall_rt_avg}ms, P95 {overall_rt_p95}ms, P99 {overall_rt_p99}ms
- 에러율: {error_rate}

**리소스 사용량** ({resource_count}개 서버)
{resource_details}

**다음 형식으로 간결하게 분석해주세요:**

종합분석 - 테스트 결과, 응답 속도, 처리율(TPS), 에러율이 전반적으로 목표치 달성 여부를 평가하고 서비스의 안정성을 확인. 최대 가상 사용자 요청 발생 시 성능 저하 문제나 병목점이 있는지 분석.

성능 모니터링 결과, 최대 사용자 부하 시 CPU/Memory 사용량 분석과 DB 서버 성능 여유도 평가. 서버 애플리케이션의 스케일 업/아웃 필요성과 개선 방향 제시.

응답시간 상세 결과 요약 - 최소, 평균 응답 시간 목표 달성 여부와 P95 기준 사용자 경험 만족도 평가.

TPS 상세결과요약 - 테스트 시나리오별 TPS 참고값과 전체 TPS 목표 비교 분석. 테스트 초반 가상 사용자 수 부족으로 인한 최소 TPS 영향도 고려.

에러율 상세결과 요약 - 평균 에러율의 목표 대비 안정성과 최대 에러율 발생 시 시스템 안정성 고려사항.

**반드시 한국어로 3-4개 문단으로 간결하게 작성하고, 이모지 사용하지 마세요.**"""

    def _get_response_time_prompt_template(self) -> str:
        """응답시간 분석 프롬프트 템플릿"""

        return """응답시간 성능을 분석해주세요. 반드시 한국어로 응답해주세요.

**응답시간 현황**
- 평균: {overall_rt_avg}ms, P50: {overall_rt_p50}ms, P95: {overall_rt_p95}ms, P99: {overall_rt_p99}ms
- 최소/최대: {overall_rt_min}ms ~ {overall_rt_max}ms
- 총 {total_requests}건 요청, {test_duration}초 지속

**분석 요청:**

응답시간 상세 결과 요약 - 최소, 평균 응답 시간이 목표를 달성하였는지 평가. P95의 경우 목표치 달성 여부와 사용자 경험에 미치는 영향. 약 몇 %의 사용자에게 원활한 서비스 제공이 가능할 것으로 예상되는지 분석.

지연 원인 진단 - P50 대비 P95 차이가 발생하는 주요 원인 분석. 예상되는 병목점(DB 연결, 네트워크 지연, GC 등)과 개선 방향 제시.

**반드시 한국어로 2-3개 문단으로 간결하게 작성하고, 이모지 사용하지 마세요.**"""

    def _get_tps_prompt_template(self) -> str:
        """TPS 분석 프롬프트 템플릿"""

        return """TPS(처리량) 성능을 분석해주세요. 반드시 한국어로 응답해주세요.

**TPS 현황**
- 목표: {target_tps} TPS, 실제: 평균 {overall_tps_avg} TPS
- 변동폭: 최소 {overall_tps_min} ~ 최대 {overall_tps_max}
- 총 처리: {total_requests}건, {test_duration}초 지속

**분석 요청:**

TPS 상세결과요약 - 테스트 시나리오별 TPS는 참고값으로만 사용하며, 전체 TPS에 대해서 목표를 비교 분석. 전체 평균 TPS가 목표에 근접하였는지 평가. TPS의 경우 테스트 초반 가상 사용자 수가 부족한 경우도 존재하므로 최소 TPS에 대해서는 참고 값으로만 사용.

처리량 제한 요인 - TPS가 제한되는 주요 병목점(CPU, DB, 네트워크 등) 분석과 현재 대비 처리량 확장 가능성 평가.

**반드시 한국어로 2-3개 문단으로 간결하게 작성하고, 이모지 사용하지 마세요.**"""

    def _get_error_rate_prompt_template(self) -> str:
        """에러율 분석 프롬프트 템플릿"""

        return """에러율 및 안정성을 분석해주세요. 반드시 한국어로 응답해주세요.

**에러 현황**
- 에러율: {error_rate} ({failed_requests}/{total_requests}건)
- 테스트: {test_duration}초간 {overall_tps_avg} TPS로 실행

**분석 요청:**

에러율 상세결과 요약 - 대부분의 경우 목표 에러율보다 안정적인지 평가. 최대 에러율의 경우 목표치보다 높은 것으로 추정되는지 분석. 요청수가 많아질 때 시스템 안정성을 고려해야 하는 부분.

에러 원인 분석 - 에러 발생 가능한 주요 원인(타임아웃, 리소스 부족, DB 병목 등) 분석과 부하 증가 시 에러율 변화 예측.

**반드시 한국어로 2-3개 문단으로 간결하게 작성하고, 이모지 사용하지 마세요.**"""

    def _get_resource_usage_prompt_template(self) -> str:
        """리소스 사용량 분석 프롬프트 템플릿"""

        return """리소스 사용량을 분석해주세요. 반드시 한국어로 응답해주세요.

**리소스 현황**
- 성능: {overall_tps_avg} TPS, {overall_rt_avg}ms 응답시간
- 서버: {resource_count}개 운영 중

**리소스 상세**
{resource_details}

**분석 요청:**

성능 모니터링 결과, 최대 사용자 부하 시 CPU 사용량이 최대치에 도달했는지, DB 서버 성능에는 여유가 있는지 분석. CPU/Memory 사용률이 적정 수준인지 평가하고 현재 상태에서 추가 부하 처리 가능 용량 분석.

리소스 효율성 - 현재 리소스로 달성한 TPS 효율성 평가와 CPU 또는 Memory 중 어느 쪽이 먼저 한계에 도달할지 분석. 서버 애플리케이션의 스케일 아웃(Scale-out)을 통한 성능 향상과 안정성 확보 방안.

**반드시 한국어로 2-3개 문단으로 간결하게 작성하고, 이모지 사용하지 마세요.**"""


def get_prompt_manager() -> PromptManager:
    """PromptManager 인스턴스 반환 (싱글톤)"""
    
    if not hasattr(get_prompt_manager, "_instance"):
        get_prompt_manager._instance = PromptManager()
    
    return get_prompt_manager._instance