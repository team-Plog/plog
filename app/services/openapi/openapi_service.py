import os
import logging
from sqlalchemy.orm import Session
from app.models.sqlite.models.project_models import OpenAPISpecModel
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.schemas.openapi_spec.plog_deploy_request import PlogConfigDTO
from app.utils.helm_executor import HelmExecutor
from app.utils.helm_values_generator import HelmValuesGenerator
from app.utils.file_writer import FileWriter

logger = logging.getLogger(__name__)


def save_openapi_spec(db: Session, openapi_spec_model: OpenAPISpecModel) -> OpenAPISpecModel:
    db.add(openapi_spec_model)
    db.commit()
    db.refresh(openapi_spec_model)

    return openapi_spec_model


async def deploy_openapi_spec(db: Session, request: PlogConfigDTO) -> dict:
    """
    PlogConfigDTO를 받아서 배포 프로세스를 실행하는 서비스
    
    Args:
        db: 데이터베이스 세션
        request: PlogConfigDTO 배포 요청 데이터
        
    Returns:
        dict: 배포 결과 정보
        
    Raises:
        EnvironmentError: PLOG_HELM_CHART_FOLDER 환경변수가 없을 때
        Exception: 배포 프로세스 실패시
    """
    try:
        logger.info(f"배포 프로세스 시작: {request.app_name}")
        
        # 1. PlogConfigDTO를 Helm values.yaml로 변환
        helm_generator = HelmValuesGenerator()
        values_yaml_content = helm_generator.generate_values_yaml(request)
        
        logger.info(f"values.yaml 생성 완료: {request.app_name}")
        
        # 2. PLOG_HELM_CHART_FOLDER 환경변수에서 경로 가져오기
        helm_chart_folder = os.getenv("PLOG_HELM_CHART_FOLDER")
        if not helm_chart_folder:
            raise EnvironmentError("PLOG_HELM_CHART_FOLDER 환경변수가 설정되지 않았습니다.")
        
        # 3. 기존 values.yaml 파일 확인 및 제거
        from pathlib import Path
        target_file_path = str(Path(helm_chart_folder) / "values.yaml")
        
        if FileWriter.file_exists(target_file_path):
            FileWriter.remove_file(target_file_path)
            logger.info(f"기존 values.yaml 파일을 제거했습니다: {target_file_path}")
        
        # 4. values.yaml 파일 저장
        saved_path = FileWriter.write_to_path(
            content=values_yaml_content,
            filename="values.yaml",
            base_path=helm_chart_folder,
        )
        
        logger.info(f"values.yaml 파일 저장 완료: {saved_path}")

        # ex) app_name = semi-medeasy -> service_name = semi_medeasy_service
        helm_executor = HelmExecutor()
        deployment_result = await helm_executor.upgrade_install(
            chart_path=helm_chart_folder,
            app_name=request.app_name,
            namespace="test"
        )

        # 5. 향후 확장 가능한 배포 결과 반환
        result = {
            "app_name": request.app_name,
            "values_yaml_path": saved_path,
            "helm_chart_folder": helm_chart_folder,
            "status": "values_generated",
            "message": f"{request.app_name} 애플리케이션의 values.yaml 파일이 생성되었습니다."
        }
        
        logger.info(f"배포 프로세스 완료: {request.app_name}")
        return result
        
    except Exception as e:
        logger.error(f"배포 프로세스 실패 - app: {request.app_name}, error: {str(e)}")
        raise Exception(f"배포 프로세스에 실패했습니다: {str(e)}")
