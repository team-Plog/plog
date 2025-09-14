"""
Helm 명령어 실행을 위한 유틸리티 클래스
helm upgrade --install 명령어를 통해 Kubernetes에 애플리케이션 배포
"""
import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HelmExecutor:
    """Helm 명령어 실행 및 배포 관리 유틸리티"""
    
    def __init__(self):
        self.default_namespace = "test"
    
    async def upgrade_install(
        self, 
        chart_path: str, 
        app_name: str, 
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        helm upgrade --install 명령어를 실행하여 애플리케이션 배포
        
        Args:
            chart_path: Helm Chart 폴더 경로
            app_name: 애플리케이션 이름 (PlogConfigDTO.app_name)
            namespace: Kubernetes 네임스페이스 (기본값: test)
            
        Returns:
            Dict[str, Any]: 배포 결과 정보
            
        Raises:
            Exception: Helm 명령어 실행 실패시
        """
        try:
            # 1. release name 생성 (app-name -> app-name-service)
            release_name = self._generate_release_name(app_name)
            target_namespace = namespace or self.default_namespace
            
            logger.info(f"Helm 배포 시작: release={release_name}, chart={chart_path}, namespace={target_namespace}")
            
            # 2. Chart.yaml 파일 존재 확인
            chart_yaml_path = Path(chart_path) / "Chart.yaml"
            if not chart_yaml_path.exists():
                raise FileNotFoundError(f"Chart.yaml 파일을 찾을 수 없습니다: {chart_yaml_path}")
            
            # 3. values.yaml 파일 존재 확인
            values_yaml_path = Path(chart_path) / "values.yaml"
            if not values_yaml_path.exists():
                raise FileNotFoundError(f"values.yaml 파일을 찾을 수 없습니다: {values_yaml_path}")
            
            # 4. helm upgrade --install 명령어 구성
            helm_command = [
                "helm", "upgrade", "--install",
                release_name,
                chart_path,
                "--namespace", target_namespace,
                "--create-namespace",
                "--wait",
                "--timeout", "300s"
            ]
            
            logger.info(f"실행할 Helm 명령어: {' '.join(helm_command)}")
            
            # 5. 비동기로 helm 명령어 실행
            result = await self._execute_helm_command(helm_command)
            
            # 6. 배포 결과 반환
            deployment_result = {
                "release_name": release_name,
                "chart_path": chart_path,
                "namespace": target_namespace,
                "status": "success" if result["returncode"] == 0 else "failed",
                "helm_output": result["stdout"],
                "helm_error": result["stderr"] if result["stderr"] else None,
                "command": " ".join(helm_command)
            }
            
            if result["returncode"] == 0:
                logger.info(f"Helm 배포 성공: {release_name}")
            else:
                logger.error(f"Helm 배포 실패: {release_name}, 에러: {result['stderr']}")
                raise Exception(f"Helm 배포에 실패했습니다: {result['stderr']}")
            
            return deployment_result
            
        except Exception as e:
            logger.error(f"Helm 배포 중 오류 발생: {str(e)}")
            raise Exception(f"Helm 배포 프로세스에 실패했습니다: {str(e)}")
    
    def _generate_release_name(self, app_name: str) -> str:
        """
        애플리케이션 이름으로부터 Helm release 이름 생성
        
        Args:
            app_name: PlogConfigDTO의 app_name (예: "semi-medeasy")
            
        Returns:
            str: Helm release 이름 (예: "semi-medeasy-service")
        """
        # 특수문자를 하이픈으로 변환하고 소문자로 정규화
        normalized_name = app_name.lower().replace("_", "-")
        return f"{normalized_name}-service"
    
    async def _execute_helm_command(self, command: list) -> Dict[str, Any]:
        """
        비동기로 helm 명령어 실행
        
        Args:
            command: 실행할 명령어 리스트
            
        Returns:
            Dict[str, Any]: 실행 결과 (returncode, stdout, stderr)
        """
        try:
            # subprocess.run을 비동기로 실행
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=None  # 현재 작업 디렉터리 사용
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else ""
            }
            
        except Exception as e:
            logger.error(f"명령어 실행 중 오류 발생: {str(e)}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    async def get_release_status(self, release_name: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        특정 Helm release의 상태 조회
        
        Args:
            release_name: Helm release 이름
            namespace: Kubernetes 네임스페이스
            
        Returns:
            Dict[str, Any]: release 상태 정보
        """
        try:
            target_namespace = namespace or self.default_namespace
            
            command = ["helm", "status", release_name, "--namespace", target_namespace, "--output", "json"]
            result = await self._execute_helm_command(command)
            
            if result["returncode"] == 0:
                import json
                status_data = json.loads(result["stdout"])
                return {
                    "status": "found",
                    "data": status_data
                }
            else:
                return {
                    "status": "not_found",
                    "error": result["stderr"]
                }
                
        except Exception as e:
            logger.error(f"Release 상태 조회 중 오류 발생: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }