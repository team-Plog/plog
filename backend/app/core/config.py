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
    KUBERNETES_TEST_NAMESPACE: str = os.getenv("KUBERNETES_TEST_NAMESPACE", "test")
    KUBERNETES_PLOG_NAMESPACE: str = os.getenv("KUBERNETES_PLOG_NAMESPACE", "plog")

    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 자동 정리 설정
    AUTO_DELETE_COMPLETED_JOBS: bool = os.getenv("AUTO_DELETE_COMPLETED_JOBS", "true").lower() == "true"
    
    # AI 분석 설정
    AI_MODEL_NAME: str = os.getenv("AI_MODEL_NAME", "llama3.1:8b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_TEMPERATURE: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
    OLLAMA_MAX_TOKENS: int = int(os.getenv("OLLAMA_MAX_TOKENS", "2000"))
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    
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

    @classmethod
    def get_ai_config(cls) -> dict:
        """AI 분석 설정을 딕셔너리로 반환"""
        return {
            "model_name": cls.AI_MODEL_NAME,
            "ollama_host": cls.OLLAMA_BASE_URL,
            "temperature": cls.OLLAMA_TEMPERATURE,
            "max_tokens": cls.OLLAMA_MAX_TOKENS,
            "timeout_seconds": cls.OLLAMA_TIMEOUT_SECONDS
        }

    @classmethod
    def validate_ai_config(cls) -> bool:
        """AI 설정 유효성 검증"""
        try:
            # 기본 값 검증
            if not cls.AI_MODEL_NAME or not cls.OLLAMA_BASE_URL:
                return False

            # 범위 검증
            if not (0.0 <= cls.OLLAMA_TEMPERATURE <= 2.0):
                return False

            if cls.OLLAMA_MAX_TOKENS < 100 or cls.OLLAMA_MAX_TOKENS > 10000:
                return False

            if cls.OLLAMA_TIMEOUT_SECONDS < 10 or cls.OLLAMA_TIMEOUT_SECONDS > 600:
                return False

            return True
        except (ValueError, TypeError):
            return False


settings = Settings()