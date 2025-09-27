"""
Helm values.yaml 파일 생성을 위한 유틸리티 클래스
PlogConfigDTO를 파싱하여 Helm Chart용 values.yaml 형식으로 변환
"""
from typing import Dict, Any, Optional
import yaml
from app.schemas.openapi_spec.plog_deploy_request import PlogConfigDTO


class HelmValuesGenerator:
    """PlogConfigDTO를 Helm Chart values.yaml 형식으로 변환하는 유틸리티"""
    
    def __init__(self):
        self.default_global_config = {
            "namespace": "test",
            "imagePullSecret": "harbor-registry-secret"
        }
    
    def generate_values_yaml(self, config: PlogConfigDTO) -> str:
        """
        PlogConfigDTO를 받아서 values.yaml 문자열을 생성
        
        Args:
            config: PlogConfigDTO 인스턴스
            
        Returns:
            str: values.yaml 형식의 문자열
        """
        values_dict = self._build_values_dict(config)
        return yaml.dump(values_dict, default_flow_style=False, allow_unicode=True, indent=2)
    
    def _build_values_dict(self, config: PlogConfigDTO) -> Dict[str, Any]:
        """values.yaml 딕셔너리 구조 생성"""
        
        # Global 설정
        global_config = self.default_global_config.copy()
        global_config["imageRegistry"] = config.image_registry_url
        
        # Application 설정
        app_config = {
            "enabled": True,
            "image": {
                "repository": f"test/{config.app_name}",
                "tag": config.image_tag or "latest"
            },
            "replicas": int(config.replicas),
            "port": int(config.port),
            "nodePort": int(config.node_port)
        }
        
        # 환경변수 설정 (모든 값에 쿼터 적용)
        if config.env:
            app_config["env"] = {key: str(value) for key, value in config.env.items()}
        
        # 리소스 설정
        if config.resources:
            app_config["resources"] = self._parse_resources(config.resources)
        
        # 볼륨 설정
        if config.volumes:
            app_config["volumes"] = self._parse_volumes(config.volumes)
        
        # 전체 구조 조립
        values = {
            "global": global_config,
            "applications": {
                config.app_name: app_config
            }
        }
        
        return values
    
    def _parse_resources(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """
        resources 딕셔너리를 Helm Chart 형식으로 변환
        
        Expected input format:
        {
            "request": {"cpu": "200m", "memory": "512Mi"},
            "limits": {"cpu": "1000m", "memory": "2Gi"}
        }
        or
        {
            "requests": {"cpu": "200m", "memory": "512Mi"},
            "limits": {"cpu": "1000m", "memory": "2Gi"}
        }
        """
        parsed_resources = {}
        
        # requests 파싱 (request/requests 둘 다 지원, 값에 쿼터 적용)
        if "request" in resources or "requests" in resources:
            requests_data = resources.get("request") or resources.get("requests")
            if requests_data:
                parsed_resources["requests"] = {key: str(value) for key, value in requests_data.items()}
        
        # limits 파싱 (값에 쿼터 적용)
        if "limits" in resources:
            parsed_resources["limits"] = {key: str(value) for key, value in resources["limits"].items()}
        
        return parsed_resources
    
    def _parse_volumes(self, volumes: Dict[str, Any]) -> Dict[str, Any]:
        """
        volumes 딕셔너리를 Helm Chart 형식으로 변환
        
        Expected input format:
        {
            "data": {
                "mountPath": "/app/data",
                "size": "10Gi"
            }
        }
        """
        # volumes 설정은 그대로 반환 (Helm Chart에서 처리)
        return volumes