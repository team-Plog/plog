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


class JobService:
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

    def list_jobs_by_prefix(self, prefix: str) -> list:
        """
        접두사로 Job 목록을 조회합니다.
        
        Args:
            prefix: Job 이름 접두사
            
        Returns:
            Job 정보 리스트
        """
        try:
            jobs = v1_batch.list_namespaced_job(namespace=self.namespace)
            matching_jobs = []
            
            for job in jobs.items:
                if job.metadata.name.startswith(prefix):
                    job_info = {
                        'name': job.metadata.name,
                        'status': self._determine_job_status(job.status),
                        'start_time': job.status.start_time,
                        'completion_time': job.status.completion_time,
                        'labels': job.metadata.labels or {}
                    }
                    matching_jobs.append(job_info)
            
            logger.info(f"Found {len(matching_jobs)} jobs with prefix '{prefix}'")
            return matching_jobs
            
        except Exception as e:
            logger.error(f"Error listing jobs by prefix {prefix}: {e}")
            return []

    def list_jobs_by_label(self, label_selector: str) -> list:
        """
        라벨 셀렉터로 Job 목록을 조회합니다.
        
        Args:
            label_selector: 라벨 셀렉터 (예: "original-job-name=load-testing")
            
        Returns:
            Job 정보 리스트
        """
        try:
            jobs = v1_batch.list_namespaced_job(
                namespace=self.namespace,
                label_selector=label_selector
            )
            job_list = []
            
            for job in jobs.items:
                job_info = {
                    'name': job.metadata.name,
                    'status': self._determine_job_status(job.status),
                    'start_time': job.status.start_time,
                    'completion_time': job.status.completion_time,
                    'labels': job.metadata.labels or {},
                    'original_job_name': job.metadata.labels.get('original-job-name', '') if job.metadata.labels else ''
                }
                job_list.append(job_info)
            
            logger.info(f"Found {len(job_list)} jobs with label selector '{label_selector}'")
            return job_list
            
        except Exception as e:
            logger.error(f"Error listing jobs by label {label_selector}: {e}")
            return []

    def list_all_jobs(self) -> list:
        """
        네임스페이스의 모든 Job을 조회합니다.
        
        Returns:
            모든 Job 정보 리스트
        """
        try:
            jobs = v1_batch.list_namespaced_job(namespace=self.namespace)
            job_list = []
            
            for job in jobs.items:
                job_info = {
                    'name': job.metadata.name,
                    'status': self._determine_job_status(job.status),
                    'start_time': job.status.start_time,
                    'completion_time': job.status.completion_time,
                    'labels': job.metadata.labels or {},
                    'original_job_name': job.metadata.labels.get('original-job-name', '') if job.metadata.labels else ''
                }
                job_list.append(job_info)
            
            logger.info(f"Found {len(job_list)} total jobs in namespace '{self.namespace}'")
            return job_list
            
        except Exception as e:
            logger.error(f"Error listing all jobs: {e}")
            return []

    def get_jobs_by_original_name(self, original_name: str) -> list:
        """
        original-job-name 라벨로 Job을 찾습니다.
        
        Args:
            original_name: 원본 Job 이름
            
        Returns:
            해당하는 Job 정보 리스트
        """
        return self.list_jobs_by_label(f"original-job-name={original_name}")

    def list_completed_jobs(self) -> list:
        """
        네임스페이스의 모든 완료된 Job을 조회합니다 (성공/실패 모두).
        
        Returns:
            완료된 Job 정보 리스트
        """
        try:
            all_jobs = self.list_all_jobs()
            completed_jobs = []
            
            for job in all_jobs:
                if job['status'] in [JobStatus.SUCCEEDED, JobStatus.FAILED]:
                    completed_jobs.append(job)
            
            logger.info(f"Found {len(completed_jobs)} completed jobs")
            return completed_jobs
            
        except Exception as e:
            logger.error(f"Error listing completed jobs: {e}")
            return []

    def list_succeeded_jobs(self) -> list:
        """
        네임스페이스의 모든 성공한 Job을 조회합니다.
        
        Returns:
            성공한 Job 정보 리스트
        """
        try:
            all_jobs = self.list_all_jobs()
            succeeded_jobs = []
            
            for job in all_jobs:
                if job['status'] == JobStatus.SUCCEEDED:
                    succeeded_jobs.append(job)
            
            logger.info(f"Found {len(succeeded_jobs)} succeeded jobs")
            return succeeded_jobs
            
        except Exception as e:
            logger.error(f"Error listing succeeded jobs: {e}")
            return []

    def list_failed_jobs(self) -> list:
        """
        네임스페이스의 모든 실패한 Job을 조회합니다.
        
        Returns:
            실패한 Job 정보 리스트
        """
        try:
            all_jobs = self.list_all_jobs()
            failed_jobs = []
            
            for job in all_jobs:
                if job['status'] == JobStatus.FAILED:
                    failed_jobs.append(job)
            
            logger.info(f"Found {len(failed_jobs)} failed jobs")
            return failed_jobs
            
        except Exception as e:
            logger.error(f"Error listing failed jobs: {e}")
            return []

    def list_running_jobs(self) -> list:
        """
        네임스페이스의 모든 실행 중인 Job을 조회합니다.
        
        Returns:
            실행 중인 Job 정보 리스트
        """
        try:
            all_jobs = self.list_all_jobs()
            running_jobs = []
            
            for job in all_jobs:
                if job['status'] == JobStatus.RUNNING:
                    running_jobs.append(job)
            
            logger.info(f"Found {len(running_jobs)} running jobs")
            return running_jobs
            
        except Exception as e:
            logger.error(f"Error listing running jobs: {e}")
            return []

    def force_delete_job(self, job_name: str) -> bool:
        """
        Job을 강제로 삭제합니다 (실행 중이어도 삭제).
        
        Args:
            job_name: 삭제할 Job 이름
            
        Returns:
            삭제 성공 여부
        """
        try:
            v1_batch.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                propagation_policy='Foreground'  # Pod들도 함께 삭제
            )
            logger.info(f"Force deleted job: {job_name}")
            return True
                
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Job {job_name} not found for deletion")
                return False
            else:
                logger.error(f"Error force deleting job {job_name}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error force deleting job {job_name}: {e}")
            return False

    def force_delete_jobs_by_original_name(self, original_name: str) -> int:
        """
        original-job-name 라벨로 모든 관련 Job들을 강제 삭제합니다.
        
        Args:
            original_name: 원본 Job 이름
            
        Returns:
            삭제된 Job 개수
        """
        try:
            jobs = self.get_jobs_by_original_name(original_name)
            deleted_count = 0
            
            for job in jobs:
                if self.force_delete_job(job['name']):
                    deleted_count += 1
            
            logger.info(f"Force deleted {deleted_count} jobs with original name '{original_name}'")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error force deleting jobs by original name {original_name}: {e}")
            return 0

    def suspend_job(self, job_name: str) -> bool:
        """
        Job을 일시정지 상태로 만듭니다 (삭제하지 않음).
        
        Args:
            job_name: 일시정지할 Job 이름
            
        Returns:
            일시정지 성공 여부
        """
        try:
            # Job 상태 확인
            job_info = self.get_job_status(job_name)
            
            if job_info['status'] in [JobStatus.SUCCEEDED, JobStatus.FAILED]:
                logger.info(f"Job {job_name} is already completed, no need to suspend")
                return True
                
            # Job의 suspend 필드를 true로 설정
            body = {
                "spec": {
                    "suspend": True
                }
            }
            
            v1_batch.patch_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                body=body
            )
            
            logger.info(f"Job {job_name} suspended successfully")
            return True
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Job {job_name} not found for suspension")
                return False
            else:
                logger.error(f"Error suspending job {job_name}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error suspending job {job_name}: {e}")
            return False

    def resume_job(self, job_name: str) -> bool:
        """
        일시정지된 Job을 재개합니다.
        
        Args:
            job_name: 재개할 Job 이름
            
        Returns:
            재개 성공 여부
        """
        try:
            # Job의 suspend 필드를 false로 설정
            body = {
                "spec": {
                    "suspend": False
                }
            }
            
            v1_batch.patch_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                body=body
            )
            
            logger.info(f"Job {job_name} resumed successfully")
            return True
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Job {job_name} not found for resume")
                return False
            else:
                logger.error(f"Error resuming job {job_name}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error resuming job {job_name}: {e}")
            return False

    def stop_running_job(self, job_name: str) -> bool:
        """
        실행 중인 Job을 중지합니다 (완료되지 않은 Job만).
        
        Args:
            job_name: 중지할 Job 이름
            
        Returns:
            중지 성공 여부
        """
        try:
            job_info = self.get_job_status(job_name)
            
            if job_info['status'] == JobStatus.RUNNING:
                return self.force_delete_job(job_name)
            elif job_info['status'] in [JobStatus.SUCCEEDED, JobStatus.FAILED]:
                logger.info(f"Job {job_name} is already completed, no need to stop")
                return True
            else:
                logger.warning(f"Job {job_name} status is {job_info['status']}, cannot determine if should stop")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping job {job_name}: {e}")
            return False

    def stop_jobs_by_original_name(self, original_name: str) -> int:
        """
        original-job-name 라벨로 실행 중인 모든 Job들을 중지합니다.
        
        Args:
            original_name: 원본 Job 이름
            
        Returns:
            중지된 Job 개수
        """
        try:
            jobs = self.get_jobs_by_original_name(original_name)
            stopped_count = 0
            
            for job in jobs:
                if job['status'] == JobStatus.RUNNING:
                    if self.force_delete_job(job['name']):
                        stopped_count += 1
                        logger.info(f"Stopped running job: {job['name']}")
            
            logger.info(f"Stopped {stopped_count} running jobs with original name '{original_name}'")
            return stopped_count
            
        except Exception as e:
            logger.error(f"Error stopping jobs by original name {original_name}: {e}")
            return 0

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