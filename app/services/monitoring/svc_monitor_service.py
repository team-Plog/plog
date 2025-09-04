from k8s.k8s_client import v1_core
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SvcMonitorService:
    """Kubernetes Service 상태 모니터링 서비스"""

    def __init__(self, namespace: str = "test"):
        self.namespace = namespace

    def get_services(self, label_selector: str = None) -> List[Dict[str, Any]]:
        """
        네임스페이스에 존재하는 Service 목록을 조회합니다.

        Args:
            label_selector: 선택적으로 label selector를 지정 (예: "app=plog-backend")

        Returns:
            Service 정보 리스트
            [
                {
                    "name": str,
                    "namespace": str,
                    "cluster_ip": str,
                    "external_ips": List[str],
                    "ports": List[Dict],
                    "type": str,
                    "selector": Dict[str, str],
                    "labels": Dict[str, str],
                },
                ...
            ]
        """
        try:
            services = v1_core.list_namespaced_service(
                namespace=self.namespace,
                label_selector=label_selector
            )

            service_list = []
            for service in services.items:
                # 포트 정보 구성
                ports = []
                if service.spec.ports:
                    for port in service.spec.ports:
                        port_info = {
                            "name": port.name,
                            "port": port.port,
                            "target_port": port.target_port,
                            "protocol": port.protocol,
                        }
                        if port.node_port:
                            port_info["node_port"] = port.node_port
                        ports.append(port_info)

                service_info = {
                    "name": service.metadata.name,
                    "namespace": service.metadata.namespace,
                    "cluster_ip": service.spec.cluster_ip,
                    "external_ips": service.spec.external_ips or [],
                    "ports": ports,
                    "type": service.spec.type,
                    "selector": service.spec.selector or {},
                    "labels": dict(service.metadata.labels) if service.metadata.labels else {},
                }
                service_list.append(service_info)

            logger.info(f"Found {len(service_list)} services in namespace {self.namespace}")
            return service_list

        except Exception as e:
            logger.error(f"Error fetching services: {e}")
            return []

    def get_pod_names_matching_service(self, service_name: str) -> List[str]:
        """
        Service와 라벨이 매칭되는 Pod name 리스트를 반환합니다.

        Args:
            service_name: Service 이름

        Returns:
            매칭되는 Pod 이름 리스트
        """
        try:
            # Service 정보 조회
            service = v1_core.read_namespaced_service(
                name=service_name, 
                namespace=self.namespace
            )

            if not service.spec.selector:
                logger.warning(f"Service {service_name} has no selector")
                return []

            # Service의 selector를 사용하여 매칭되는 Pod 조회
            selector_labels = []
            for key, value in service.spec.selector.items():
                selector_labels.append(f"{key}={value}")
            
            label_selector = ",".join(selector_labels)
            
            pods = v1_core.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )

            pod_names = [pod.metadata.name for pod in pods.items]
            
            logger.info(f"Found {len(pod_names)} pods matching service {service_name}")
            return pod_names

        except Exception as e:
            logger.error(f"Error finding pods for service {service_name}: {e}")
            return []

    def get_pods_for_all_services(self) -> Dict[str, List[str]]:
        """
        네임스페이스의 모든 Service와 매칭되는 Pod 목록을 반환합니다.

        Returns:
            Service 이름을 키로 하고 Pod 이름 리스트를 값으로 하는 딕셔너리
            {
                "service-name": ["pod1", "pod2", ...],
                ...
            }
        """
        service_pod_mapping = {}
        
        try:
            services = self.get_services()
            
            for service in services:
                service_name = service["name"]
                pod_names = self.get_pod_names_matching_service(service_name)
                service_pod_mapping[service_name] = pod_names
                
            return service_pod_mapping
            
        except Exception as e:
            logger.error(f"Error getting pods for all services: {e}")
            return {}

    def get_service_endpoints(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Service의 Endpoints 정보를 조회합니다.

        Args:
            service_name: Service 이름

        Returns:
            Endpoints 정보
            {
                "name": str,
                "namespace": str,
                "subsets": [
                    {
                        "addresses": [{"ip": str, "hostname": str, "node_name": str}],
                        "ports": [{"name": str, "port": int, "protocol": str}]
                    }
                ]
            }
        """
        try:
            endpoints = v1_core.read_namespaced_endpoints(
                name=service_name,
                namespace=self.namespace
            )

            subsets = []
            if endpoints.subsets:
                for subset in endpoints.subsets:
                    addresses = []
                    if subset.addresses:
                        for addr in subset.addresses:
                            address_info = {"ip": addr.ip}
                            if addr.hostname:
                                address_info["hostname"] = addr.hostname
                            if addr.node_name:
                                address_info["node_name"] = addr.node_name
                            addresses.append(address_info)

                    ports = []
                    if subset.ports:
                        for port in subset.ports:
                            port_info = {
                                "name": port.name,
                                "port": port.port,
                                "protocol": port.protocol,
                            }
                            ports.append(port_info)

                    subsets.append({
                        "addresses": addresses,
                        "ports": ports
                    })

            endpoints_info = {
                "name": endpoints.metadata.name,
                "namespace": endpoints.metadata.namespace,
                "subsets": subsets
            }

            return endpoints_info

        except Exception as e:
            logger.error(f"Error getting endpoints for service {service_name}: {e}")
            return None

    def get_service_by_labels(self, labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        라벨을 기반으로 Service를 조회합니다.

        Args:
            labels: 검색할 라벨 딕셔너리

        Returns:
            매칭되는 Service 정보 리스트
        """
        label_selector = ",".join([f"{key}={value}" for key, value in labels.items()])
        return self.get_services(label_selector=label_selector)