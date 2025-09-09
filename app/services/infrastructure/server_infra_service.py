import logging
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.sqlite.models.project_models import ServerInfraModel
from app.models.sqlite.database import SessionLocal

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

    def get_existing_pod_names_by_group(self, db: Session, group_name: str, namespace: str = "test") -> List[str]:
        """
        특정 그룹(서비스)의 이미 저장된 Pod 이름 목록을 반환합니다.
        
        Args:
            db: 데이터베이스 세션
            group_name: 그룹 이름 (서비스 이름)
            namespace: 네임스페이스
            
        Returns:
            해당 그룹의 저장된 Pod 이름 리스트
        """
        try:
            existing_pods = db.query(ServerInfraModel).filter(
                ServerInfraModel.group_name == group_name,
                ServerInfraModel.namespace == namespace
            ).all()
            
            return [pod.name for pod in existing_pods]
            
        except Exception as e:
            logger.error(f"Error getting existing pod names for group {group_name}: {e}")
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


def get_job_pods_with_service_types(job_name: str) -> List[Dict[str, str]]:
    """
    Job 이름으로 관련 Pod 목록과 service_type 조회
    
    간단한 경로: job_name → TestHistory → ScenarioHistory → ServerInfra
    
    Args:
        job_name: Job 이름
        
    Returns:
        List[Dict]: [{"pod_name": "api-server-123", "service_type": "SERVER"}, ...]
    """
    # 순환참조 방지를 위해 지연 import
    from app.services.testing.test_history_service import get_test_history_by_job_name
    
    db = SessionLocal()
    try:
        # 1. job_name으로 TestHistory 조회
        test_history = get_test_history_by_job_name(db, job_name)
        if not test_history:
            logger.warning(f"No test history found for job: {job_name}")
            return []
        
        pod_info_list = []
        processed_pods = set()  # 중복 제거용
        
        # 2. TestHistory의 scenario들에서 각각의 server_infra 정보 추출
        for scenario in test_history.scenarios:
            try:
                endpoint = scenario.endpoint
                if not endpoint or not endpoint.openapi_spec_version:
                    logger.debug(f"Skipping scenario {scenario.id} - missing endpoint or spec version")
                    continue
                
                openapi_spec = endpoint.openapi_spec_version.openapi_spec
                if not openapi_spec or not openapi_spec.server_infras:
                    logger.debug(f"Skipping scenario {scenario.id} - missing openapi spec or server infras")
                    continue
                
                # 3. 각 server_infra에서 Pod 정보 추출
                for server_infra in openapi_spec.server_infras:
                    if server_infra.name and server_infra.name not in processed_pods:
                        pod_info = {
                            "pod_name": server_infra.name,
                            "service_type": server_infra.service_type or "SERVER"  # 기본값 SERVER
                        }
                        pod_info_list.append(pod_info)
                        processed_pods.add(server_infra.name)
                        
                        logger.debug(f"Found pod: {server_infra.name} (type: {server_infra.service_type})")
                
            except Exception as e:
                logger.error(f"Error processing scenario {scenario.id}: {e}")
                continue
        
        logger.info(f"Found {len(pod_info_list)} pods for job {job_name}: "
                   f"{[p['pod_name'] for p in pod_info_list]}")
        
        return pod_info_list
        
    except Exception as e:
        logger.error(f"Error getting pods for job {job_name}: {e}")
        return []
    finally:
        db.close()


async def get_job_pods_with_service_types_async(
        db: AsyncSession,
        job_name: str
) -> List[Dict[str, str]]:
    """
    Job 이름으로 관련 Pod 목록과 service_type 조회 (비동기 버전)
    
    간단한 경로: job_name → TestHistory → ScenarioHistory → ServerInfra
    
    Args:
        db: AsyncSession 
        job_name: Job 이름
        
    Returns:
        List[Dict]: [{"pod_name": "api-server-123", "service_type": "SERVER"}, ...]
    """
    # 순환참조 방지를 위해 지연 import
    from app.services.testing.test_history_service import get_test_history_by_job_name_async
    
    try:
        # 1. job_name으로 TestHistory 조회
        test_history = await get_test_history_by_job_name_async(db, job_name)
        if not test_history:
            logger.warning(f"No test history found for job: {job_name}")
            return []
        
        pod_info_list = []
        processed_pods = set()  # 중복 제거용
        
        # 2. TestHistory의 scenario들에서 각각의 server_infra 정보 추출
        for scenario in test_history.scenarios:
            try:
                endpoint = scenario.endpoint
                if not endpoint or not endpoint.openapi_spec_version:
                    logger.debug(f"Skipping scenario {scenario.id} - missing endpoint or spec version")
                    continue
                
                openapi_spec = endpoint.openapi_spec_version.openapi_spec
                if not openapi_spec or not openapi_spec.server_infras:
                    logger.debug(f"Skipping scenario {scenario.id} - missing openapi spec or server infras")
                    continue
                
                # 3. 각 server_infra에서 Pod 정보 추출
                for server_infra in openapi_spec.server_infras:
                    if server_infra.name and server_infra.name not in processed_pods:
                        pod_info = {
                            "pod_name": server_infra.name,
                            "service_type": server_infra.service_type or "SERVER"  # 기본값 SERVER
                        }
                        pod_info_list.append(pod_info)
                        processed_pods.add(server_infra.name)
                        
                        logger.debug(f"Found pod: {server_infra.name} (type: {server_infra.service_type})")
                
            except Exception as e:
                logger.error(f"Error processing scenario {scenario.id}: {e}")
                continue
        
        logger.info(f"Found {len(pod_info_list)} pods for job {job_name}: "
                   f"{[p['pod_name'] for p in pod_info_list]}")
        
        return pod_info_list
        
    except Exception as e:
        logger.error(f"Error getting pods for job {job_name}: {e}")
        return []