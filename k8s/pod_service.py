from k8s.k8s_client import v1_batch, v1_core, v1_apps
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PodService:
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

    def get_pod_details_with_owner_info(self, pod_name: str) -> Optional[Dict[str, Any]]:
        """
        Pod의 상세 정보와 ownerReferences를 추적하여 반환합니다.
        
        Args:
            pod_name: Pod 이름
            
        Returns:
            Pod 상세 정보와 owner 정보
            {
                "name": str,
                "namespace": str,
                "labels": dict,
                "images": List[str],
                "resource_type": str,  # "POD", "REPLICASET", "DEPLOYMENT"
                "group_name": str,     # ReplicaSet 또는 Deployment 이름
                "service_type": str,   # "SERVER" 또는 "DATABASE"
            }
        """
        try:
            # Pod 정보 조회
            pod = v1_core.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            
            # Pod 기본 정보
            pod_info = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "labels": dict(pod.metadata.labels) if pod.metadata.labels else {},
                "images": [container.image for container in pod.spec.containers],
            }
            
            # ownerReferences 추적
            resource_type = "POD"
            group_name = None
            
            if pod.metadata.owner_references:
                owner = pod.metadata.owner_references[0]
                
                if owner.kind == "ReplicaSet":
                    # ReplicaSet에서 Deployment 찾기
                    try:
                        rs = v1_apps.read_namespaced_replica_set(
                            name=owner.name, 
                            namespace=self.namespace
                        )
                        
                        if rs.metadata.owner_references:
                            deployment_owner = rs.metadata.owner_references[0]
                            if deployment_owner.kind == "Deployment":
                                resource_type = "DEPLOYMENT"
                                group_name = deployment_owner.name
                            else:
                                resource_type = "REPLICASET"
                                group_name = owner.name
                        else:
                            resource_type = "REPLICASET"
                            group_name = owner.name
                            
                    except Exception as e:
                        logger.warning(f"Failed to read ReplicaSet {owner.name}: {e}")
                        resource_type = "REPLICASET"
                        group_name = owner.name
                        
                elif owner.kind == "Deployment":
                    resource_type = "DEPLOYMENT"
                    group_name = owner.name
                else:
                    resource_type = owner.kind.upper()
                    group_name = owner.name
            
            pod_info.update({
                "resource_type": resource_type,
                "group_name": group_name,
                "service_type": self._determine_service_type(pod_info["images"])
            })
            
            return pod_info
            
        except Exception as e:
            logger.error(f"Error getting pod details for {pod_name}: {e}")
            return None
    
    def _determine_service_type(self, images: List[str]) -> str:
        """
        Pod의 이미지를 기반으로 서비스 타입을 결정합니다.
        
        Args:
            images: Pod의 컨테이너 이미지 리스트
            
        Returns:
            "SERVER" 또는 "DATABASE"
        """
        database_images = [
            "mysql", "postgres", "postgresql", "redis", "mongodb", "mongo",
            "mariadb", "elasticsearch", "cassandra", "dynamodb", "influxdb"
        ]
        
        for image in images:
            image_lower = image.lower()
            for db_image in database_images:
                if db_image in image_lower:
                    return "DATABASE"
        
        return "SERVER"

    def get_pod_db_connections(self, pod_name: str) -> List[Dict[str, str]]:
        """
        Pod의 환경변수와 ConfigMap을 통해 데이터베이스 연결 정보를 추적합니다.
        
        Args:
            pod_name: Pod 이름
            
        Returns:
            데이터베이스 연결 정보 리스트
            [
                {
                    "db_type": str,      # "mysql", "postgresql", "redis", etc.
                    "db_host": str,      # 데이터베이스 호스트
                    "db_port": str,      # 데이터베이스 포트
                    "db_name": str,      # 데이터베이스 이름
                    "source": str        # "env" 또는 "configmap"
                },
                ...
            ]
        """
        db_connections = []
        
        try:
            pod = v1_core.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            
            for container in pod.spec.containers:
                # 환경변수에서 DB 연결 정보 추출
                if container.env:
                    db_info = self._extract_db_info_from_env(container.env)
                    if db_info:
                        db_info["source"] = "env"
                        db_connections.append(db_info)
                
                # envFrom (ConfigMap/Secret)에서 DB 연결 정보 추출
                if container.env_from:
                    for env_from in container.env_from:
                        if env_from.config_map_ref:
                            db_info = self._extract_db_info_from_configmap(
                                env_from.config_map_ref.name
                            )
                            if db_info:
                                db_info["source"] = "configmap"
                                db_connections.append(db_info)
            
            return db_connections
            
        except Exception as e:
            logger.error(f"Error getting DB connections for pod {pod_name}: {e}")
            return []

    def _extract_db_info_from_env(self, env_vars) -> Optional[Dict[str, str]]:
        """
        환경변수에서 데이터베이스 연결 정보를 추출합니다.
        """
        db_info = {}
        
        for env_var in env_vars:
            name = env_var.name.upper()
            value = env_var.value if env_var.value else ""
            
            # 일반적인 DB 환경변수 패턴들
            if any(pattern in name for pattern in ['DB_HOST', 'DATABASE_HOST', 'MYSQL_HOST', 'POSTGRES_HOST', 'REDIS_HOST']):
                db_info["db_host"] = value
            elif any(pattern in name for pattern in ['DB_PORT', 'DATABASE_PORT', 'MYSQL_PORT', 'POSTGRES_PORT', 'REDIS_PORT']):
                db_info["db_port"] = value
            elif any(pattern in name for pattern in ['DB_NAME', 'DATABASE_NAME', 'MYSQL_DATABASE', 'POSTGRES_DB']):
                db_info["db_name"] = value
            elif 'MYSQL' in name:
                db_info["db_type"] = "mysql"
            elif any(pattern in name for pattern in ['POSTGRES', 'POSTGRESQL']):
                db_info["db_type"] = "postgresql"
            elif 'REDIS' in name:
                db_info["db_type"] = "redis"
            elif 'MONGODB' in name or 'MONGO' in name:
                db_info["db_type"] = "mongodb"
        
        # 최소한 호스트 정보가 있어야 유효한 DB 연결로 간주
        return db_info if db_info.get("db_host") else None

    def _extract_db_info_from_configmap(self, configmap_name: str) -> Optional[Dict[str, str]]:
        """
        ConfigMap에서 데이터베이스 연결 정보를 추출합니다.
        """
        try:
            configmap = v1_core.read_namespaced_config_map(
                name=configmap_name, 
                namespace=self.namespace
            )
            
            if not configmap.data:
                return None
            
            db_info = {}
            
            for key, value in configmap.data.items():
                key_upper = key.upper()
                
                if any(pattern in key_upper for pattern in ['DB_HOST', 'DATABASE_HOST', 'MYSQL_HOST', 'POSTGRES_HOST', 'REDIS_HOST']):
                    db_info["db_host"] = value
                elif any(pattern in key_upper for pattern in ['DB_PORT', 'DATABASE_PORT', 'MYSQL_PORT', 'POSTGRES_PORT', 'REDIS_PORT']):
                    db_info["db_port"] = value
                elif any(pattern in key_upper for pattern in ['DB_NAME', 'DATABASE_NAME', 'MYSQL_DATABASE', 'POSTGRES_DB']):
                    db_info["db_name"] = value
                elif 'MYSQL' in key_upper:
                    db_info["db_type"] = "mysql"
                elif any(pattern in key_upper for pattern in ['POSTGRES', 'POSTGRESQL']):
                    db_info["db_type"] = "postgresql"
                elif 'REDIS' in key_upper:
                    db_info["db_type"] = "redis"
                elif 'MONGODB' in key_upper or 'MONGO' in key_upper:
                    db_info["db_type"] = "mongodb"
            
            return db_info if db_info.get("db_host") else None
            
        except Exception as e:
            logger.error(f"Error reading ConfigMap {configmap_name}: {e}")
            return None

    def find_services_for_pod(self, pod_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Pod의 라벨을 기반으로 연결된 Service를 찾습니다.
        
        Args:
            pod_labels: Pod의 라벨 딕셔너리
            
        Returns:
            연결된 Service 정보 리스트
            [
                {
                    "name": str,
                    "ports": List[int],
                    "cluster_ip": str,
                    "type": str
                },
                ...
            ]
        """
        services = []
        
        try:
            # 네임스페이스의 모든 서비스 조회
            service_list = v1_core.list_namespaced_service(namespace=self.namespace)
            
            for service in service_list.items:
                # Service의 selector와 Pod의 label이 매치되는지 확인
                if service.spec.selector and self._labels_match(service.spec.selector, pod_labels):
                    # 일반 포트와 NodePort 정보를 모두 포함
                    ports = []
                    node_ports = []
                    port_mappings = {}  # NodePort -> Service Port 매핑
                    if service.spec.ports:
                        for port in service.spec.ports:
                            ports.append(port.port)
                            if port.node_port:  # NodePort가 있는 경우
                                node_ports.append(port.node_port)
                                port_mappings[port.node_port] = port.port  # NodePort -> Service Port 매핑
                    
                    service_info = {
                        "name": service.metadata.name,
                        "ports": ports,
                        "node_ports": node_ports,
                        "port_mappings": port_mappings,  # NodePort -> Service Port 매핑 추가
                        "cluster_ip": service.spec.cluster_ip,
                        "type": service.spec.type
                    }
                    services.append(service_info)
                    
            return services
            
        except Exception as e:
            logger.error(f"Error finding services for pod labels {pod_labels}: {e}")
            return []

    def find_workloads_for_pod(self, pod_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Pod labels와 매치되는 모든 워크로드(Deployment, StatefulSet, DaemonSet, ReplicaSet)를 조회합니다.

        Args:
            pod_labels: Pod의 labels

        Returns:
            워크로드 정보 리스트 (replica 정보 포함)
            [
                {
                    "type": str,                    # "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"
                    "name": str,                    # 워크로드 이름
                    "namespace": str,               # 네임스페이스
                    "desired_replicas": int,        # 원하는 replica 수
                    "current_replicas": int,        # 현재 replica 수
                    "ready_replicas": int,          # 준비된 replica 수
                    "updated_replicas": int,        # 업데이트된 replica 수
                    "labels": Dict[str, str],       # 워크로드 labels
                    "creation_timestamp": datetime  # 생성 시간
                },
                ...
            ]

        Note:
            - DaemonSet의 경우 desired_replicas는 desired_number_scheduled 값을 사용
            - ReplicaSet의 경우 updated_replicas는 replicas 값을 사용 (updated_replicas 필드가 없음)
            - 모든 워크로드 타입에서 동일한 형식의 replica 정보 제공
        """
        workloads = []

        # Deployment 조회
        workloads.extend(self._find_deployments(pod_labels))

        # StatefulSet 조회
        workloads.extend(self._find_statefulsets(pod_labels))

        # DaemonSet 조회
        workloads.extend(self._find_daemonsets(pod_labels))

        # ReplicaSet 조회 (주로 Deployment가 관리하지만 독립적으로 존재할 수 있음)
        workloads.extend(self._find_replicasets(pod_labels))

        return workloads

    def _find_deployments(self, pod_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """Deployment 조회"""
        deployments = []

        try:
            deployment_list = v1_apps.list_namespaced_deployment(namespace=self.namespace)

            for deployment in deployment_list.items:
                if deployment.spec.selector and self._labels_match(deployment.spec.selector.match_labels, pod_labels):
                    deployment_info = {
                        "type": "Deployment",
                        "name": deployment.metadata.name,
                        "namespace": deployment.metadata.namespace,
                        "desired_replicas": deployment.spec.replicas or 0,
                        "current_replicas": deployment.status.replicas or 0,
                        "ready_replicas": deployment.status.ready_replicas or 0,
                        "updated_replicas": deployment.status.updated_replicas or 0,
                        "labels": deployment.metadata.labels or {},
                        "creation_timestamp": deployment.metadata.creation_timestamp
                    }
                    deployments.append(deployment_info)

            return deployments

        except Exception as e:
            logger.error(f"Error finding deployments for pod labels {pod_labels}: {e}")
            return []

    def _find_statefulsets(self, pod_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """StatefulSet 조회"""
        statefulsets = []

        try:
            statefulset_list = v1_apps.list_namespaced_stateful_set(namespace=self.namespace)

            for statefulset in statefulset_list.items:
                if statefulset.spec.selector and self._labels_match(statefulset.spec.selector.match_labels, pod_labels):
                    statefulset_info = {
                        "type": "StatefulSet",
                        "name": statefulset.metadata.name,
                        "namespace": statefulset.metadata.namespace,
                        "desired_replicas": statefulset.spec.replicas or 0,
                        "current_replicas": statefulset.status.replicas or 0,
                        "ready_replicas": statefulset.status.ready_replicas or 0,
                        "updated_replicas": statefulset.status.updated_replicas or 0,
                        "labels": statefulset.metadata.labels or {},
                        "creation_timestamp": statefulset.metadata.creation_timestamp
                    }
                    statefulsets.append(statefulset_info)

            return statefulsets

        except Exception as e:
            logger.error(f"Error finding statefulsets for pod labels {pod_labels}: {e}")
            return []

    def _find_daemonsets(self, pod_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """DaemonSet 조회"""
        daemonsets = []

        try:
            daemonset_list = v1_apps.list_namespaced_daemon_set(namespace=self.namespace)

            for daemonset in daemonset_list.items:
                if daemonset.spec.selector and self._labels_match(daemonset.spec.selector.match_labels, pod_labels):
                    daemonset_info = {
                        "type": "DaemonSet",
                        "name": daemonset.metadata.name,
                        "namespace": daemonset.metadata.namespace,
                        "desired_replicas": daemonset.status.desired_number_scheduled or 0,
                        "current_replicas": daemonset.status.current_number_scheduled or 0,
                        "ready_replicas": daemonset.status.number_ready or 0,
                        "updated_replicas": daemonset.status.updated_number_scheduled or 0,
                        "labels": daemonset.metadata.labels or {},
                        "creation_timestamp": daemonset.metadata.creation_timestamp
                    }
                    daemonsets.append(daemonset_info)

            return daemonsets

        except Exception as e:
            logger.error(f"Error finding daemonsets for pod labels {pod_labels}: {e}")
            return []

    def _find_replicasets(self, pod_labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """ReplicaSet 조회"""
        replicasets = []

        try:
            replicaset_list = v1_apps.list_namespaced_replica_set(namespace=self.namespace)

            for replicaset in replicaset_list.items:
                if replicaset.spec.selector and self._labels_match(replicaset.spec.selector.match_labels, pod_labels):
                    replicaset_info = {
                        "type": "ReplicaSet",
                        "name": replicaset.metadata.name,
                        "namespace": replicaset.metadata.namespace,
                        "desired_replicas": replicaset.spec.replicas or 0,
                        "current_replicas": replicaset.status.replicas or 0,
                        "ready_replicas": replicaset.status.ready_replicas or 0,
                        "updated_replicas": replicaset.status.replicas or 0,  # ReplicaSet은 updated_replicas가 없어서 replicas 사용
                        "labels": replicaset.metadata.labels or {},
                        "creation_timestamp": replicaset.metadata.creation_timestamp
                    }
                    replicasets.append(replicaset_info)

            return replicasets

        except Exception as e:
            logger.error(f"Error finding replicasets for pod labels {pod_labels}: {e}")
            return []

    def _labels_match(self, selector: Dict[str, str], pod_labels: Dict[str, str]) -> bool:
        """
        Service selector와 Pod labels가 매치되는지 확인합니다.
        """
        for key, value in selector.items():
            if key not in pod_labels or pod_labels[key] != value:
                return False
        return True

    def discover_swagger_urls(self, services: List[Dict[str, Any]]) -> List[str]:
        """
        Service 정보를 기반으로 가능한 Swagger URL들을 탐지합니다.
        
        Args:
            services: Service 정보 리스트
            
        Returns:
            발견된 Swagger URL 리스트
        """
        swagger_urls = []
        
        # 일반적인 Swagger 엔드포인트 패턴들
        swagger_paths = [
            "/swagger-ui/index.html",
            "/swagger-ui",
            "/swagger",
            "/api/swagger",
            "/docs",
            "/api/docs",
            "/api-docs",
            "/v1/api-docs",
            "/v2/api-docs",
            "/v3/api-docs",
            "/openapi.json",
            "/swagger.json"
        ]
        
        for service in services:
            service_name = service["name"]
            cluster_ip = service["cluster_ip"]
            ports = service["ports"]
            
            for port in ports:
                # HTTP 포트로 추정되는 포트들 (일반적으로 80, 8080, 3000, 4000, 5000, 8000 등)
                if port in [80, 8080, 3000, 4000, 5000, 8000, 9000] or 8000 <= port <= 9999:
                    base_url = f"http://{cluster_ip}:{port}"
                    
                    for swagger_path in swagger_paths:
                        potential_url = f"{base_url}{swagger_path}"
                        
                        if self._check_swagger_url(potential_url):
                            swagger_urls.append(potential_url)
                            logger.info(f"Found Swagger URL: {potential_url}")
                            
        return swagger_urls

    def is_pod_ready(self, pod_name: str) -> bool:
        """
        Pod의 readiness 상태를 확인합니다.

        Args:
            pod_name: 확인할 Pod 이름

        Returns:
            Pod가 준비 상태인지 여부
        """
        try:
            pod = v1_core.read_namespaced_pod(name=pod_name, namespace=self.namespace)

            # Pod가 Running 상태이고 모든 컨테이너가 Ready 상태인지 확인
            if pod.status.phase != "Running":
                logger.debug(f"Pod {pod_name} is not in Running phase: {pod.status.phase}")
                return False

            # 컨테이너별 Ready 상태 확인
            if pod.status.container_statuses:
                for container_status in pod.status.container_statuses:
                    if not container_status.ready:
                        logger.debug(f"Container {container_status.name} in pod {pod_name} is not ready")
                        return False

            # readiness probe가 설정된 경우 상태 확인
            if pod.status.conditions:
                for condition in pod.status.conditions:
                    if condition.type == "Ready":
                        if condition.status != "True":
                            logger.debug(f"Pod {pod_name} readiness condition is not True: {condition.status}")
                            return False
                        break

            logger.debug(f"Pod {pod_name} is ready")
            return True

        except Exception as e:
            logger.error(f"Error checking pod readiness for {pod_name}: {e}")
            return False

    def get_pod_container_ports(self, pod_name: str) -> List[int]:
        """
        Pod의 모든 컨테이너 포트를 조회합니다.

        Args:
            pod_name: Pod 이름

        Returns:
            Pod의 컨테이너 포트 리스트
        """
        try:
            pod = v1_core.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            ports = []

            for container in pod.spec.containers:
                if container.ports:
                    for port in container.ports:
                        if port.container_port:
                            ports.append(port.container_port)

            return list(set(ports))  # 중복 제거

        except Exception as e:
            logger.error(f"Error getting container ports for pod {pod_name}: {e}")
            return []

    def _check_swagger_url(self, url: str, timeout: int = 3) -> bool:
        """
        주어진 URL이 유효한 Swagger 엔드포인트인지 확인합니다.

        Args:
            url: 확인할 URL
            timeout: 타임아웃 (초)

        Returns:
            유효한 Swagger 엔드포인트인지 여부
        """
        try:
            response = requests.get(url, timeout=timeout)

            if response.status_code == 200:
                content = response.text.lower()
                # Swagger 관련 키워드들이 포함되어 있는지 확인
                swagger_keywords = [
                    "swagger", "openapi", "api documentation",
                    "swagger-ui", "redoc", "rapidoc"
                ]

                if any(keyword in content for keyword in swagger_keywords):
                    return True

                # JSON 응답인 경우 OpenAPI 스펙인지 확인
                try:
                    json_data = response.json()
                    if isinstance(json_data, dict) and (
                        "swagger" in json_data or
                        "openapi" in json_data or
                        "info" in json_data
                    ):
                        return True
                except:
                    pass

        except Exception as e:
            logger.debug(f"Failed to check Swagger URL {url}: {e}")

        return False