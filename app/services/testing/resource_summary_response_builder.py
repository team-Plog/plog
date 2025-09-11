from typing import Any, Dict, List
from app.services.testing.resource_response_builder import TestHistoryResourcesResponseBuilder, \
    ResourceProcessingContext
from app.utils.metrics_calculator import MetricsCalculator, MetricStats
from app.repositories.scenario_history_repository import ScenarioHistoryRepository
from app.repositories.test_history_repository import TestHistoryRepository
from app.repositories.test_resource_timeseries_repository import TestResourceTimeseriesRepository
from k8s.resource_service import ResourceService


class SummaryResourcesResponseBuilder(TestHistoryResourcesResponseBuilder):
    
    def __init__(
        self,
        test_history_repository: TestHistoryRepository,
        scenario_history_repository: ScenarioHistoryRepository,
        test_resource_timeseries_repository: TestResourceTimeseriesRepository,
        resource_service: ResourceService
    ):
        """Constructor Dependency Injection"""
        super().__init__(
            test_history_repository=test_history_repository,
            scenario_history_repository=scenario_history_repository,
            test_resource_timeseries_repository=test_resource_timeseries_repository,
            resource_service=resource_service
        )
    async def _build_final_response(self, context: ResourceProcessingContext) -> List[Dict[str, Any]]:
        pod_info_list = context.pod_info_list
        resource_timeseries = context.resource_timeseries

        # Pod별로 리소스 데이터 그룹화
        pod_resource_map = {}

        # resource_timeseries를 pod_name별로 그룹화
        for resource in resource_timeseries:
            if resource.server_infra and resource.server_infra.name:
                pod_name = resource.server_infra.name
                if pod_name not in pod_resource_map:
                    pod_resource_map[pod_name] = []
                pod_resource_map[pod_name].append(resource)

        # pod_info_list와 매칭하여 최종 응답 구성
        result = []

        for pod_info in pod_info_list:
            pod_name = pod_info["pod_name"]
            service_type = pod_info["service_type"]

            # 해당 Pod의 리소스 데이터 조회
            pod_resources = pod_resource_map.get(pod_name, [])

            if not pod_resources:
                continue

            # MetricsCalculator를 사용하여 통계 계산
            stats = MetricsCalculator.calculate_resource_summary(pod_resources)

            cpu_stats = stats['cpu']
            memory_stats = stats['memory']

            # 리소스 limit 값 추출 (첫 번째 레코드에서)
            cpu_limit = pod_resources[0].cpu_limit_millicores if pod_resources and pod_resources[
                0].cpu_limit_millicores else 1000
            memory_limit = pod_resources[0].memory_limit_mb if pod_resources and pod_resources[
                0].memory_limit_mb else 1024

            # 백분율 계산을 위한 값들 추출
            cpu_values = MetricsCalculator.extract_metric_values(pod_resources, 'cpu')
            memory_values = MetricsCalculator.extract_metric_values(pod_resources, 'memory')

            # 백분율 계산
            cpu_percent_stats = MetricsCalculator.calculate_percentage_stats(
                cpu_values, [cpu_limit] * len(cpu_values)
            ) if cpu_values else MetricStats(0.0, 0.0, 0.0, 0)

            memory_percent_stats = MetricsCalculator.calculate_percentage_stats(
                memory_values, [memory_limit] * len(memory_values)
            ) if memory_values else MetricStats(0.0, 0.0, 0.0, 0)

            result.append({
                "pod_name": pod_name,
                "service_type": service_type,
                "cpu_usage_summary": {
                    "usage": {
                        "max": cpu_stats.max_value,
                        "min": cpu_stats.min_value,
                        "avg": cpu_stats.avg_value,
                    },
                    "percent": {
                        "max": cpu_percent_stats.max_value,
                        "min": cpu_percent_stats.min_value,
                        "avg": cpu_percent_stats.avg_value,
                    },
                    "cpu_limit": cpu_limit,
                    "count": cpu_stats.count
                },
                "memory_usage_summary": {
                    "usage": {
                        "max": memory_stats.max_value,
                        "min": memory_stats.min_value,
                        "avg": memory_stats.avg_value,
                    },
                    "percent": {
                        "max": memory_percent_stats.max_value,
                        "min": memory_percent_stats.min_value,
                        "avg": memory_percent_stats.avg_value,
                    },
                    "memory_limit": memory_limit,
                    "count": memory_stats.count
                }
            })

        return result

