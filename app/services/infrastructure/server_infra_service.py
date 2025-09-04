import logging
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.sqlite.models.project_models import ServerInfraModel
from app.db.sqlite.database import SessionLocal

logger = logging.getLogger(__name__)


class ServerInfraService:
    """ServerInfra 테이블 관련 서비스"""

    def get_existing_pod_names(self, db: Session, namespace: str = "test") -> List[str]:
        """
        이미 저장된 Pod 이름 목록을 반환합니다.
        
        Args:
            db: 데이터베이스 세션
            namespace: 네임스페이스
            
        Returns:
            저장된 Pod 이름 리스트
        """
        try:
            existing_pods = db.query(ServerInfraModel).filter(
                ServerInfraModel.namespace == namespace
            ).all()
            
            return [pod.name for pod in existing_pods]
            
        except Exception as e:
            logger.error(f"Error getting existing pod names: {e}")
            return []

    def create_server_infra(self, db: Session, pod_info: Dict[str, Any], 
                           open_api_spec_id: Optional[int] = None) -> Optional[ServerInfraModel]:
        """
        새로운 ServerInfra 레코드를 생성합니다.
        
        Args:
            db: 데이터베이스 세션
            pod_info: Pod 정보 딕셔너리
            open_api_spec_id: 연결될 OpenAPI Spec ID (선택사항)
            
        Returns:
            생성된 ServerInfraModel 인스턴스
        """
        try:
            server_infra = ServerInfraModel(
                open_api_spec_id=open_api_spec_id,
                resource_type=pod_info.get("resource_type"),
                environment="K3S",  # 고정값
                service_type=pod_info.get("service_type"),
                name=pod_info.get("name"),
                group_name=pod_info.get("group_name"),
                label=pod_info.get("labels", {}),
                namespace=pod_info.get("namespace")
            )
            
            db.add(server_infra)
            db.commit()
            db.refresh(server_infra)
            
            logger.info(f"Created server_infra record for pod: {pod_info.get('name')}")
            return server_infra
            
        except Exception as e:
            logger.error(f"Error creating server_infra record: {e}")
            db.rollback()
            return None

    def get_server_infra_by_name(self, db: Session, name: str, namespace: str = "test") -> Optional[ServerInfraModel]:
        """
        이름으로 ServerInfra 레코드를 조회합니다.
        
        Args:
            db: 데이터베이스 세션
            name: Pod 이름
            namespace: 네임스페이스
            
        Returns:
            ServerInfraModel 인스턴스 또는 None
        """
        try:
            return db.query(ServerInfraModel).filter(
                ServerInfraModel.name == name,
                ServerInfraModel.namespace == namespace
            ).first()
            
        except Exception as e:
            logger.error(f"Error getting server_infra by name {name}: {e}")
            return None

    def get_server_infra_exists_group_names(self, db: Session) -> List[str]:
        stmt = select(ServerInfraModel.group_name).distinct()
        result = db.execute(stmt).scalars().all()

        return result

    def get_server_infra_group_names_with_openapi_spec_id(self, db: Session)-> List[Tuple[int, str]]:
        stmt = select(ServerInfraModel.openapi_spec_id, ServerInfraModel.group_name).distinct()
        result = db.execute(stmt).all()

        return result

    def update_server_infra_openapi_spec(self, db: Session, server_infra_id: int,
                                        open_api_spec_id: int) -> bool:
        """
        ServerInfra의 open_api_spec_id를 업데이트합니다.
        
        Args:
            db: 데이터베이스 세션
            server_infra_id: ServerInfra ID
            open_api_spec_id: OpenAPI Spec ID
            
        Returns:
            업데이트 성공 여부
        """
        try:
            server_infra = db.query(ServerInfraModel).filter(
                ServerInfraModel.id == server_infra_id
            ).first()
            
            if server_infra:
                server_infra.open_api_spec_id = open_api_spec_id
                db.commit()
                logger.info(f"Updated server_infra {server_infra_id} with openapi_spec {open_api_spec_id}")
                return True
            else:
                logger.warning(f"ServerInfra with id {server_infra_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error updating server_infra openapi_spec: {e}")
            db.rollback()
            return False

    def get_unlinked_server_pods(self, db: Session, namespace: str = "test") -> List[ServerInfraModel]:
        """
        OpenAPI Spec과 연결되지 않은 서버 Pod들을 반환합니다.
        
        Args:
            db: 데이터베이스 세션
            namespace: 네임스페이스
            
        Returns:
            연결되지 않은 서버 Pod 리스트
        """
        try:
            return db.query(ServerInfraModel).filter(
                ServerInfraModel.namespace == namespace,
                ServerInfraModel.service_type == "SERVER",
                ServerInfraModel.open_api_spec_id.is_(None)
            ).all()
            
        except Exception as e:
            logger.error(f"Error getting unlinked server pods: {e}")
            return []