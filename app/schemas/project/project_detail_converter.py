from typing import List, Dict, Any
from app.models.sqlite.models.project_models import ProjectModel, OpenAPISpecModel, EndpointModel


class ProjectDetailConverter:
    """반정규화된 endpoint 구조를 기존 응답 형식으로 변환하는 컨버터"""
    
    @staticmethod
    def convert_to_response(project: ProjectModel) -> Dict[str, Any]:
        """
        반정규화된 ProjectModel을 기존 응답 형식으로 변환
        
        Args:
            project: 조회된 ProjectModel 인스턴스
            
        Returns:
            기존 응답 형식과 동일한 구조의 딕셔너리
        """
        response_data = {
            "id": project.id,
            "title": project.title,
            "summary": project.summary,
            "description": project.description,
            "openapi_specs": []
        }
        
        for spec in project.openapi_specs:
            spec_data = ProjectDetailConverter._convert_openapi_spec(spec)
            response_data["openapi_specs"].append(spec_data)
        
        return response_data
    
    @staticmethod
    def _convert_openapi_spec(spec: OpenAPISpecModel) -> Dict[str, Any]:
        """
        OpenAPISpecModel을 응답 형식으로 변환하면서 endpoint들을 tag별로 그룹화
        
        Args:
            spec: OpenAPISpecModel 인스턴스
            
        Returns:
            tag별로 그룹화된 OpenAPI spec 데이터
        """
        # endpoint들을 tag별로 그룹화
        tags_dict = {}
        activate_spec = spec.openapi_spec_versions[0]
        
        for endpoint in activate_spec.endpoints:
            tag_name = endpoint.tag_name or "Default"
            tag_description = endpoint.tag_description or ""
            
            # 태그가 처음 등장하는 경우 초기화
            if tag_name not in tags_dict:
                tags_dict[tag_name] = {
                    "id": ProjectDetailConverter._generate_tag_id(tag_name),
                    "name": tag_name,
                    "description": tag_description,
                    "endpoints": []
                }
            
            # endpoint 데이터 변환 후 추가
            endpoint_data = ProjectDetailConverter._convert_endpoint(endpoint)
            tags_dict[tag_name]["endpoints"].append(endpoint_data)
        
        return {
            "id": spec.id,
            "title": spec.title,
            "version": spec.version,
            "base_url": spec.base_url,
            "tags": list(tags_dict.values())
        }
    
    @staticmethod
    def _convert_endpoint(endpoint: EndpointModel) -> Dict[str, Any]:
        """
        EndpointModel을 응답 형식으로 변환
        
        Args:
            endpoint: EndpointModel 인스턴스
            
        Returns:
            endpoint 응답 데이터
        """
        return {
            "id": endpoint.id,
            "path": endpoint.path,
            "method": endpoint.method,
            "summary": endpoint.summary,
            "description": endpoint.description,
            "parameters": [
                {
                    "id": param.id,
                    "param_type": param.param_type,
                    "name": param.name,
                    "required": param.required,
                    "value_type": param.value_type,
                    "title": param.title,
                    "description": param.description,
                    "value": param.value
                }
                for param in endpoint.parameters
            ]
        }
    
    @staticmethod
    def _generate_tag_id(tag_name: str) -> int:
        """
        태그명으로부터 일관된 ID 생성
        
        Args:
            tag_name: 태그명
            
        Returns:
            생성된 태그 ID (해시값 기반)
        """
        return abs(hash(tag_name)) % 2147483647