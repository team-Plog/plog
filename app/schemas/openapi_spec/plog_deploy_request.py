from typing import Optional, Dict, Any, Union

from pydantic import BaseModel, Field

class PlogConfigDTO(BaseModel):
    """plog.json 구조를 그대로 받는 DTO (언더스코어 버전)"""

    image_registry_url: str = Field(...)
    app_name: str = Field(...)
    replicas: Union[str, int] = Field(...)  # 문자열/숫자 둘 다 허용
    node_port: Union[str, int] = Field(...)
    port: Union[str, int] = Field(...)
    image_tag: Optional[str] = None
    git_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # 유연한 구조로 설계
    resources: Optional[Dict[str, Any]] = Field(default_factory=dict)
    volumes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    env: Dict[str, str] = Field(default_factory=dict)

    class Config:
        extra = "allow"  # 정의되지 않은 필드도 허용 (확장성)
        json_schema_extra = {
            "example": {
                "image_registry_url": "35.216.24.11:32000",
                "plog_backend_url": "35.216.24.11:30002",
                "app_name": "semi-medeasy",
                "replicas": "2",
                "node_port": "30500",
                "port": "8080",
                "image_tag": "abc1234",
                "git_info": {
                    "commit_sha": "abc1234",
                    "commit_message": "plog: 새로운 기능 추가 및 버그 수정",
                    "commit_author": "developer@company.com",
                    "build_time": "2025-09-12T15:30:45+09:00",
                    "full_image_name": "35.216.24.11:32000/test/semi-medeasy:abc1234"
                },
                "resources": {
                    "request": {
                        "cpu": "200m",
                        "memory": "512Mi"
                    },
                    "limits": {
                        "cpu": "1000m",
                        "memory": "2Gi"
                    }
                },
                "volumes": {
                    "data": {
                        "mountPath": "/app/data",
                        "size": "10Gi"
                    }
                },
                "env": {
                    "DB_HOST": "semi-medeasy-db-svc-headless",
                    "DB_PORT": "5432",
                    "TOKEN_SECRET_KEY": "fefewfwefjiwfjiwfejiwfjiwefjwefeif",
                    "ACCESS_TOKEN_HOUR": "300",
                    "REFRESH_TOKEN_HOUR": "600",
                    "REDIS_JWT_HOST": "semi-medeasy-redis-service",
                    "REDIS_JWT_PORT": "6379",
                    "REDIS_JWT_PASSWORD": "medeasy1234"
                }
            }
        }