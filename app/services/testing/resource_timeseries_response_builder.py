from typing import Any, Dict, List

from app.services.testing.resource_response_builder import TestHistoryResourcesResponseBuilder, \
    ResourceProcessingContext
from app.repositories.scenario_history_repository import ScenarioHistoryRepository
from app.repositories.test_history_repository import TestHistoryRepository
from app.repositories.test_resource_timeseries_repository import TestResourceTimeseriesRepository
from k8s.resource_service import ResourceService


class TimeseriesResourcesResponseBuilder(TestHistoryResourcesResponseBuilder):
    
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

            # 타임스탬프별로 CPU/Memory 데이터 그룹화
            timestamp_data_map = {}

            for resource in pod_resources:
                timestamp_str = resource.timestamp.isoformat()

                # 타임스탬프별 데이터 그룹화 - 첫 번째 레코드의 리소스 스펙 사용
                if timestamp_str not in timestamp_data_map:
                    timestamp_data_map[timestamp_str] = {
                        'timestamp': timestamp_str,
                        'cpu_value': None,
                        'memory_value': None,
                        'cpu_request': resource.cpu_request_millicores,
                        'cpu_limit': resource.cpu_limit_millicores,
                        'memory_request': resource.memory_request_mb,
                        'memory_limit': resource.memory_limit_mb
                    }

                # CPU/Memory 값 설정
                if resource.metric_type == 'cpu':
                    timestamp_data_map[timestamp_str]['cpu_value'] = resource.value
                elif resource.metric_type == 'memory':
                    timestamp_data_map[timestamp_str]['memory_value'] = resource.value

            # 완전한 데이터만 선별하고 응답 형식으로 변환
            resource_data = []

            for timestamp_str, data in timestamp_data_map.items():
                if data['cpu_value'] is not None and data['memory_value'] is not None:
                    # 사용률 계산 (limit 기준)
                    cpu_percent = (data['cpu_value'] / data['cpu_limit'] * 100) if data['cpu_limit'] and data[
                        'cpu_limit'] > 0 else 0
                    memory_percent = (data['memory_value'] / data['memory_limit'] * 100) if data['memory_limit'] and \
                                                                                            data[
                                                                                                'memory_limit'] > 0 else 0

                    resource_data.append({
                        "timestamp": timestamp_str,
                        "usage": {
                            "cpu_percent": round(cpu_percent, 2),
                            "memory_percent": round(memory_percent, 2),
                            "cpu_is_predicted": False,
                            "memory_is_predicted": False
                        },
                        "actual_usage": {
                            "cpu_millicores": data['cpu_value'],
                            "memory_mb": data['memory_value']
                        },
                        "specs": {
                            "cpu_request_millicores": data['cpu_request'],
                            "cpu_limit_millicores": data['cpu_limit'],
                            "memory_request_mb": data['memory_request'],
                            "memory_limit_mb": data['memory_limit']
                        }
                    })

            # 타임스탬프순으로 정렬
            resource_data.sort(key=lambda x: x['timestamp'])

            result.append({
                "pod_name": pod_name,
                "service_type": service_type,
                "resource_data": resource_data
            })

        return result