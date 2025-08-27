from k8s.k8s_client import v1_batch, v1_core
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PodMonitorService:
    """Kubernetes Pod 상태 모니터링 서비스"""

    def __init__(self, namespace: str = "test"):
        self.namespace = namespace

    def get_running_pods(self, label_selector: str = None) -> List[Dict[str, Any]]:
        """
        실행 중인 Pod 리스트를 조회합니다.

        Args:
            label_selector: 선택적으로 label selector를 지정 (예: "app=plog-backend")

        Returns:
            실행 중인 Pod 정보 리스트
            [
                {
                    "name": str,
                    "namespace": str,
                    "node": str,
                    "phase": str,
                    "start_time": datetime,
                    "pod_ip": str
                },
                ...
            ]
        """
        try:
            pods = v1_core.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector
            )

            running_pods = []
            for pod in pods.items:
                if pod.status.phase == "Running":
                    pod_info = {
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "node": pod.spec.node_name,
                        "phase": pod.status.phase,
                        "start_time": pod.status.start_time,
                        "pod_ip": pod.status.pod_ip,
                    }
                    running_pods.append(pod_info)

            logger.info(f"Found {len(running_pods)} running pods in namespace {self.namespace}")
            return running_pods

        except Exception as e:
            logger.error(f"Error fetching running pods: {e}")
            return []