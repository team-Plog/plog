import logging
from datetime import datetime
from typing import Optional, Dict, Any
from kubernetes.client.rest import ApiException
from k8s.k8s_client import v1_batch, v1_core

logger = logging.getLogger(__name__)


class JobStatus:
    """k8s Job 상태 상수"""
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class JobMonitorService:
    """Kubernetes Job 상태 모니터링 서비스"""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace

    def get_job_status(self, job_name: str) -> Dict[str, Any]:
        """
        Job 상태와 관련 정보를 조회합니다.
        
        Args:
            job_name: 조회할 Job 이름
            
        Returns:
            Job 상태 정보 딕셔너리
            {
                'status': 'Running|Succeeded|Failed|Unknown',
                'start_time': datetime,
                'completion_time': datetime,
                'conditions': list,
                'active_pods': int,
                'succeeded_pods': int,
                'failed_pods': int
            }
        """
        try:
            job = v1_batch.read_namespaced_job(name=job_name, namespace=self.namespace)
            status = job.status
            
            # Job 상태 판단
            job_status = self._determine_job_status(status)
            
            result = {
                'status': job_status,
                'start_time': status.start_time,
                'completion_time': status.completion_time,
                'conditions': status.conditions or [],
                'active_pods': status.active or 0,
                'succeeded_pods': status.succeeded or 0,
                'failed_pods': status.failed or 0,
                'parallelism': job.spec.parallelism,
                'completions': job.spec.completions
            }
            
            logger.info(f"Job {job_name} status: {job_status}")
            return result
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Job {job_name} not found")
                return {'status': JobStatus.UNKNOWN, 'error': 'Job not found'}
            else:
                logger.error(f"Error getting job status for {job_name}: {e}")
                return {'status': JobStatus.UNKNOWN, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting job status for {job_name}: {e}")
            return {'status': JobStatus.UNKNOWN, 'error': str(e)}

    def _determine_job_status(self, status) -> str:
        """Job 상태 객체를 기반으로 상태를 판단합니다."""
        if status.conditions:
            for condition in status.conditions:
                if condition.type == "Complete" and condition.status == "True":
                    return JobStatus.SUCCEEDED
                elif condition.type == "Failed" and condition.status == "True":
                    return JobStatus.FAILED
        
        # 활성 Pod가 있으면 실행 중
        if status.active and status.active > 0:
            return JobStatus.RUNNING
            
        # 완료된 Pod가 있지만 조건이 없으면 성공으로 간주
        if status.succeeded and status.succeeded > 0:
            return JobStatus.SUCCEEDED
            
        return JobStatus.UNKNOWN

    def is_job_completed(self, job_name: str) -> bool:
        """Job이 완료되었는지 확인합니다."""
        job_info = self.get_job_status(job_name)
        return job_info['status'] in [JobStatus.SUCCEEDED, JobStatus.FAILED]

    def is_job_succeeded(self, job_name: str) -> bool:
        """Job이 성공적으로 완료되었는지 확인합니다."""
        job_info = self.get_job_status(job_name)
        return job_info['status'] == JobStatus.SUCCEEDED

    def get_job_duration(self, job_name: str) -> Optional[float]:
        """
        Job 실행 시간을 초 단위로 반환합니다.
        
        Returns:
            실행 시간(초) 또는 None (완료되지 않은 경우)
        """
        job_info = self.get_job_status(job_name)
        
        start_time = job_info.get('start_time')
        completion_time = job_info.get('completion_time')
        
        if start_time and completion_time:
            duration = (completion_time - start_time).total_seconds()
            return duration
        elif start_time and job_info['status'] == JobStatus.RUNNING:
            # 실행 중인 경우 현재까지의 시간
            duration = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
            return duration
            
        return None

    def get_job_pods(self, job_name: str) -> list:
        """Job과 연관된 Pod 목록을 조회합니다."""
        try:
            # Job의 selector를 사용하여 Pod 조회
            pods = v1_core.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"job-name={job_name}"
            )
            
            pod_list = []
            for pod in pods.items:
                pod_info = {
                    'name': pod.metadata.name,
                    'phase': pod.status.phase,
                    'start_time': pod.status.start_time,
                    'completion_time': getattr(pod.status.container_statuses[0] if pod.status.container_statuses else None, 'finished_at', None)
                }
                pod_list.append(pod_info)
            
            return pod_list
            
        except Exception as e:
            logger.error(f"Error getting pods for job {job_name}: {e}")
            return []

    def delete_completed_job(self, job_name: str) -> bool:
        """완료된 Job을 삭제합니다."""
        try:
            if self.is_job_completed(job_name):
                v1_batch.delete_namespaced_job(
                    name=job_name,
                    namespace=self.namespace,
                    propagation_policy='Background'
                )
                logger.info(f"Deleted completed job: {job_name}")
                return True
            else:
                logger.warning(f"Job {job_name} is not completed, skipping deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting job {job_name}: {e}")
            return False