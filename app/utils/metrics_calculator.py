from typing import List, Dict
from dataclasses import dataclass


@dataclass
class MetricStats:
    """메트릭 통계 결과"""
    max_value: float
    min_value: float
    avg_value: float
    count: int


class MetricsCalculator:
    """리소스 메트릭 통계 계산 유틸리티"""
    
    @staticmethod
    def calculate_basic_stats(values: List[float]) -> MetricStats:
        """
        기본 통계 계산 (max, min, avg, count)
        
        Args:
            values: 계산할 값들의 리스트
            
        Returns:
            MetricStats: 통계 결과 (max, min, avg, count)
        """
        if not values:
            return MetricStats(0.0, 0.0, 0.0, 0)
            
        max_val = max(values)
        min_val = min(values)
        count = len(values)
        avg_val = sum(values) / count
        
        return MetricStats(max_val, min_val, avg_val, count)
    
    @staticmethod
    def extract_metric_values(resources: List, metric_type: str, value_field: str = 'value') -> List[float]:
        """
        특정 메트릭 타입의 값들을 추출
        
        Args:
            resources: 리소스 객체 리스트
            metric_type: 추출할 메트릭 타입 ('cpu', 'memory')
            value_field: 값이 저장된 필드명 (기본: 'value')
            
        Returns:
            List[float]: 추출된 값들의 리스트
        """
        return [
            getattr(resource, value_field) 
            for resource in resources 
            if getattr(resource, 'metric_type', None) == metric_type
        ]
    
    @staticmethod
    def calculate_resource_summary(resources: List) -> Dict[str, MetricStats]:
        """
        리소스 목록에서 CPU/Memory 통계를 한 번에 계산
        
        Args:
            resources: 리소스 객체 리스트
            
        Returns:
            Dict[str, MetricStats]: CPU/Memory 통계 결과
                - 'cpu': CPU 메트릭 통계
                - 'memory': Memory 메트릭 통계
        """
        cpu_values = MetricsCalculator.extract_metric_values(resources, 'cpu')
        memory_values = MetricsCalculator.extract_metric_values(resources, 'memory')
        
        return {
            'cpu': MetricsCalculator.calculate_basic_stats(cpu_values),
            'memory': MetricsCalculator.calculate_basic_stats(memory_values)
        }
    
    @staticmethod
    def calculate_percentage_stats(actual_values: List[float], limit_values: List[float]) -> MetricStats:
        """
        실제값/제한값 기준 백분율 통계 계산
        
        Args:
            actual_values: 실제 사용량 값들
            limit_values: 제한값들
            
        Returns:
            MetricStats: 백분율 통계 결과
        """
        if not actual_values or not limit_values or len(actual_values) != len(limit_values):
            return MetricStats(0.0, 0.0, 0.0, 0)
            
        percentages = [
            (actual / limit * 100) if limit > 0 else 0.0 
            for actual, limit in zip(actual_values, limit_values)
        ]
        
        return MetricsCalculator.calculate_basic_stats(percentages)