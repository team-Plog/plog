import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """애플리케이션 설정"""
    
    # 스케줄러 설정
    SCHEDULER_POLL_INTERVAL: int = int(os.getenv("SCHEDULER_POLL_INTERVAL", "15"))  # 15초로 단축
    SCHEDULER_MAX_RETRY: int = int(os.getenv("SCHEDULER_MAX_RETRY", "3"))
    SCHEDULER_METRICS_DELAY: int = int(os.getenv("SCHEDULER_METRICS_DELAY", "30"))  # 초
    SCHEDULER_JOB_TIMEOUT_HOURS: int = int(os.getenv("SCHEDULER_JOB_TIMEOUT_HOURS", "4"))
    SCHEDULER_JOB_WARNING_HOURS: int = int(os.getenv("SCHEDULER_JOB_WARNING_HOURS", "1"))
    
    # InfluxDB 설정
    INFLUXDB_HOST: str = os.getenv("INFLUXDB_HOST", "localhost")
    INFLUXDB_PORT: str = os.getenv("INFLUXDB_PORT", "8086")
    INFLUXDB_DATABASE: str = os.getenv("INFLUXDB_DATABASE", "k6")
    
    # k6 설정
    K6_SCRIPT_FILE_FOLDER: str = os.getenv("K6_SCRIPT_FILE_FOLDER", "/mnt/k6-scripts")
    K6_DEFAULT_PVC: str = os.getenv("K6_DEFAULT_PVC", "k6-script-pvc")
    
    # Kubernetes 설정
    KUBERNETES_NAMESPACE: str = os.getenv("KUBERNETES_NAMESPACE", "default")
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 자동 정리 설정
    AUTO_DELETE_COMPLETED_JOBS: bool = os.getenv("AUTO_DELETE_COMPLETED_JOBS", "true").lower() == "true"
    
    @classmethod
    def get_scheduler_config(cls) -> dict:
        """스케줄러 설정을 딕셔너리로 반환"""
        return {
            "poll_interval": cls.SCHEDULER_POLL_INTERVAL,
            "max_retry_attempts": cls.SCHEDULER_MAX_RETRY,
            "metrics_delay": cls.SCHEDULER_METRICS_DELAY,
            "job_timeout_hours": cls.SCHEDULER_JOB_TIMEOUT_HOURS,
            "job_warning_hours": cls.SCHEDULER_JOB_WARNING_HOURS,
            "auto_delete_jobs": cls.AUTO_DELETE_COMPLETED_JOBS
        }


settings = Settings()