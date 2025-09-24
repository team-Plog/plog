import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from kubernetes import client, config
from kubernetes.client.rest import ApiException as K8sApiException

logger = logging.getLogger(__name__)

class DeployService:
    """
    Kubernetes 배포 정보 조회 서비스
    Git hooks를 통해 배포된 애플리케이션의 상세 정보를 조회하고 추출
    """

    def __init__(self):
        """Kubernetes 클라이언트 초기화"""
        try:
            # 클러스터 내부에서 실행되는 경우
            config.load_incluster_config()
        except config.ConfigException:
            # 로컬에서 실행되는 경우
            config.load_kube_config()

        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()

    def get_deployment_details(self, deployment_name: str, namespace: str = "test") -> Optional[Dict[str, Any]]:
        """
            {
          "metadata": {
            "name": "semi-medeasy-deployment",
            "namespace": "test",
            "creationTimestamp": "2025-09-19T13:40:16Z",
            "labels": {
              "app": "semi-medeasy",
              "app.kubernetes.io/managed-by": "Helm",
              "chart": "plog-test-apps",
              "release": "semi-medeasy-service"
            },
            "annotations": {
              "deployment.kubernetes.io/revision": "9",
              "meta.helm.sh/release-name": "semi-medeasy-service",
              "meta.helm.sh/release-namespace": "test"
            }
          },
          "spec": {
            "replicas": 4,
            "selector": {
              "matchLabels": {
                "app": "semi-medeasy"
              }
            },
            "strategy": {
              "type": "RollingUpdate",
              "rollingUpdate": {
                "maxUnavailable": "25%",
                "maxSurge": "25%"
              }
            },
            "template": {
              "metadata": {
                "labels": {
                  "app": "semi-medeasy",
                  "release": "semi-medeasy-service"
                },
                "annotations": {
                  "kubectl.kubernetes.io/restartedAt": "2025-09-22T09:43:30+09:00"
                }
              },
              "spec": {
                "containers": [
                  {
                    "name": "semi-medeasy-container",
                    "image": "registry.example.com/test/semi-medeasy:abcdef0",
                    "ports": [
                      {"containerPort": 8080, "protocol": "TCP"}
                    ],
                    "resources": {
                      "limits": {"cpu": "1", "memory": "2000Mi"},
                      "requests": {"cpu": "200m", "memory": "500Mi"}
                    },
                    "env": [
                      {"name": "ACCESS_TOKEN_HOUR", "value": "300"},
                      {"name": "DB_HOST", "value": "semi-medeasy-db-svc-headless"},
                      {"name": "DB_NAME", "value": "medeasy"},
                      {"name": "DB_PASSWORD", "value": "****"},
                      {"name": "DB_PORT", "value": "5432"},
                      {"name": "DB_USERNAME", "value": "medeasy"},
                      {"name": "REDIS_JWT_HOST", "value": "semi-medeasy-redis-svc"},
                      {"name": "REDIS_JWT_PASSWORD", "value": "****"},
                      {"name": "REDIS_JWT_PORT", "value": "6379"},
                      {"name": "REFRESH_TOKEN_HOUR", "value": "600"},
                      {"name": "TOKEN_SECRET_KEY", "value": "****"}
                    ]
                  }
                ]
              }
            }
          },
          "status": {
            "replicas": 4,
            "updatedReplicas": 4,
            "availableReplicas": 0,
            "unavailableReplicas": 4,
            "conditions": [
              {
                "type": "Progressing",
                "status": "True",
                "reason": "NewReplicaSetAvailable"
              },
              {
                "type": "Available",
                "status": "False",
                "reason": "MinimumReplicasUnavailable"
              }
            ],
            "observedGeneration": 9
          }
        }
    """
        try:
            deployment_info = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )

            return deployment_info

        except K8sApiException as e:
            logger.error(f"Failed to get deployment {deployment_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting deployment {deployment_name}: {e}")
            return None

    def _extract_resource_info(self, deployment) -> Dict[str, Any]:
        """
        Deployment에서 리소스 정보 추출

        Args:
            deployment: Kubernetes Deployment 객체

        Returns:
            Dict[str, Any]: 리소스 정보 (request, limits)
        """
        resource_info = {
            "request": {"cpu": None, "memory": None},
            "limits": {"cpu": None, "memory": None}
        }

        try:
            container = deployment.spec.template.spec.containers[0]
            if container.resources:
                # Requests 정보
                if container.resources.requests:
                    resource_info["request"]["cpu"] = container.resources.requests.get("cpu")
                    resource_info["request"]["memory"] = container.resources.requests.get("memory")

                # Limits 정보
                if container.resources.limits:
                    resource_info["limits"]["cpu"] = container.resources.limits.get("cpu")
                    resource_info["limits"]["memory"] = container.resources.limits.get("memory")

        except (AttributeError, IndexError) as e:
            logger.warning(f"Failed to extract resource info: {e}")

        return resource_info

    def _extract_container_info(self, deployment) -> List[Dict[str, Any]]:
        """
        Deployment에서 컨테이너 정보 추출

        Args:
            deployment: Kubernetes Deployment 객체

        Returns:
            List[Dict[str, Any]]: 컨테이너 정보 리스트
        """
        containers = []

        try:
            for container in deployment.spec.template.spec.containers:
                container_info = {
                    "name": container.name,
                    "image": container.image,
                    "ports": [{"containerPort": port.container_port} for port in (container.ports or [])],
                    "env": [{"name": env.name, "value": env.value} for env in (container.env or [])]
                }
                containers.append(container_info)

        except Exception as e:
            logger.warning(f"Failed to extract container info: {e}")

        return containers

    def create_default_version_detail_from_deployment(self,
                                                     deployment_name: str,
                                                     namespace: str = "test") -> Dict[str, Any]:
        """
        Deployment 정보로부터 기본 version detail 데이터를 생성
        Git hooks 없이 배포된 경우 사용

        Args:
            deployment_name (str): 배포명
            namespace (str): 네임스페이스

        Returns:
            Dict[str, Any]: 기본 version detail 데이터
        """
        detail_info = self.extract_version_detail_info(deployment_name, namespace)

        if not detail_info:
            # 기본값 반환
            return {
                "replicas": 1,
                "resources": {
                    "request": {"cpu": "100m", "memory": "128Mi"},
                    "limits": {"cpu": "500m", "memory": "512Mi"}
                }
            }

        return {
            "replicas": detail_info["replicas"] or 1,
            "resources": detail_info["resources"]
        }

    def find_deployment_name_from_pod(self, pod_name: str, namespace: str = "test") -> Optional[str]:
        """
        Pod 이름으로부터 실제 Deployment 이름을 찾기
        Pod -> ReplicaSet -> Deployment owner reference 추적
        """
        try:
            # Pod 정보 조회
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

            # Pod의 owner reference에서 ReplicaSet 찾기
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        replicaset_name = owner.name

                        # ReplicaSet 정보 조회
                        replicaset = self.apps_v1.read_namespaced_replica_set(
                            name=replicaset_name, namespace=namespace
                        )

                        # ReplicaSet의 owner reference에서 Deployment 찾기
                        if replicaset.metadata.owner_references:
                            for rs_owner in replicaset.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    return rs_owner.name

            logger.warning(f"Could not find deployment for pod: {pod_name}")
            return None

        except Exception as e:
            logger.error(f"Error finding deployment for pod {pod_name}: {e}")
            return None