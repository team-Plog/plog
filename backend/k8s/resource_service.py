from k8s.k8s_client import v1_core
import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ResourceService:
    """Kubernetes Pod Resource 조회 서비스"""

    def __init__(self, namespace: str = "test"):
        self.namespace = namespace

    def get_pod_resource_specs(self, pod_name: str) -> Optional[Dict[str, Any]]:
        """
        Pod의 모든 컨테이너 resource spec을 조회합니다.
        
        Args:
            pod_name: Pod 이름
            
        Returns:
            Pod resource spec 정보
            {
                "pod_name": str,
                "namespace": str,
                "containers": [
                    {
                        "name": str,
                        "cpu_request_millicores": float,
                        "cpu_limit_millicores": float,
                        "memory_request_mb": float,
                        "memory_limit_mb": float
                    },
                    ...
                ]
            }
        """
        try:
            pod = v1_core.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            
            containers_resources = []
            
            for container in pod.spec.containers:
                container_resource = {
                    "name": container.name,
                    "cpu_request_millicores": 0.0,
                    "cpu_limit_millicores": 0.0,
                    "memory_request_mb": 0.0,
                    "memory_limit_mb": 0.0
                }
                
                # Resource requests 파싱
                if container.resources and container.resources.requests:
                    requests = container.resources.requests
                    
                    if "cpu" in requests:
                        container_resource["cpu_request_millicores"] = self._parse_cpu_to_millicores(requests["cpu"])
                    
                    if "memory" in requests:
                        container_resource["memory_request_mb"] = self._parse_memory_to_mb(requests["memory"])
                
                # Resource limits 파싱
                if container.resources and container.resources.limits:
                    limits = container.resources.limits
                    
                    if "cpu" in limits:
                        container_resource["cpu_limit_millicores"] = self._parse_cpu_to_millicores(limits["cpu"])
                    
                    if "memory" in limits:
                        container_resource["memory_limit_mb"] = self._parse_memory_to_mb(limits["memory"])
                
                containers_resources.append(container_resource)
            
            result = {
                "pod_name": pod_name,
                "namespace": self.namespace,
                "containers": containers_resources
            }
            
            logger.info(f"Retrieved resource specs for pod {pod_name}: {len(containers_resources)} containers")
            return result
            
        except Exception as e:
            logger.error(f"Error getting pod resource specs for {pod_name}: {e}")
            return None

    def get_pod_aggregated_resources(self, pod_name: str) -> Optional[Dict[str, float]]:
        """
        Pod의 모든 컨테이너 리소스를 합계하여 반환합니다.
        
        Args:
            pod_name: Pod 이름
            
        Returns:
            집계된 리소스 정보
            {
                "cpu_request_millicores": float,
                "cpu_limit_millicores": float,
                "memory_request_mb": float,
                "memory_limit_mb": float
            }
        """
        try:
            pod_specs = self.get_pod_resource_specs(pod_name)
            
            if not pod_specs:
                return None
            
            aggregated = {
                "cpu_request_millicores": 0.0,
                "cpu_limit_millicores": 0.0,
                "memory_request_mb": 0.0,
                "memory_limit_mb": 0.0
            }
            
            for container in pod_specs["containers"]:
                aggregated["cpu_request_millicores"] += container["cpu_request_millicores"]
                aggregated["cpu_limit_millicores"] += container["cpu_limit_millicores"]
                aggregated["memory_request_mb"] += container["memory_request_mb"]
                aggregated["memory_limit_mb"] += container["memory_limit_mb"]
            
            logger.info(f"Aggregated resource specs for pod {pod_name}: "
                       f"CPU req={aggregated['cpu_request_millicores']}m, "
                       f"CPU limit={aggregated['cpu_limit_millicores']}m, "
                       f"Memory req={aggregated['memory_request_mb']}MB, "
                       f"Memory limit={aggregated['memory_limit_mb']}MB")
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating pod resource specs for {pod_name}: {e}")
            return None

    def get_multiple_pods_resources(self, pod_names: List[str]) -> Dict[str, Optional[Dict[str, float]]]:
        """
        여러 Pod의 집계된 리소스를 한 번에 조회합니다.
        
        Args:
            pod_names: Pod 이름 리스트
            
        Returns:
            Pod별 집계된 리소스 정보
            {
                "pod-name-1": {
                    "cpu_request_millicores": float,
                    "cpu_limit_millicores": float,
                    "memory_request_mb": float,
                    "memory_limit_mb": float
                },
                "pod-name-2": {...},
                ...
            }
        """
        results = {}
        
        for pod_name in pod_names:
            results[pod_name] = self.get_pod_aggregated_resources(pod_name)
        
        logger.info(f"Retrieved resource specs for {len(pod_names)} pods")
        return results

    def _parse_cpu_to_millicores(self, cpu_value: str) -> float:
        """
        CPU 값을 millicores 단위로 변환합니다.
        
        Args:
            cpu_value: CPU 값 (예: "500m", "1", "0.5")
            
        Returns:
            millicores 단위 CPU 값
        """
        try:
            cpu_str = str(cpu_value).lower().strip()
            
            # millicores 단위 (예: "500m")
            if cpu_str.endswith('m'):
                return float(cpu_str[:-1])
            
            # cores 단위 (예: "1", "0.5")
            else:
                return float(cpu_str) * 1000
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse CPU value '{cpu_value}': {e}")
            return 0.0

    def _parse_memory_to_mb(self, memory_value: str) -> float:
        """
        Memory 값을 MB 단위로 변환합니다.
        
        Args:
            memory_value: Memory 값 (예: "512Mi", "1Gi", "1024000000", "1G")
            
        Returns:
            MB 단위 Memory 값
        """
        try:
            memory_str = str(memory_value).strip()
            
            # 숫자만 있는 경우 (bytes 단위로 가정)
            if memory_str.isdigit():
                return float(memory_str) / (1024 * 1024)
            
            # 단위가 있는 경우 파싱
            match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Za-z]+)$', memory_str)
            if not match:
                logger.warning(f"Cannot parse memory value: {memory_value}")
                return 0.0
            
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # 단위별 MB 변환
            if unit in ['b', 'byte', 'bytes']:
                return value / (1024 * 1024)
            elif unit in ['k', 'kb', 'ki', 'kib']:
                return value / 1024
            elif unit in ['m', 'mb', 'mi', 'mib']:
                return value
            elif unit in ['g', 'gb', 'gi', 'gib']:
                return value * 1024
            elif unit in ['t', 'tb', 'ti', 'tib']:
                return value * 1024 * 1024
            elif unit in ['p', 'pb', 'pi', 'pib']:
                return value * 1024 * 1024 * 1024
            else:
                logger.warning(f"Unknown memory unit: {unit}")
                return 0.0
                
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to parse memory value '{memory_value}': {e}")
            return 0.0