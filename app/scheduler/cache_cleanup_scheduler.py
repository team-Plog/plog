import asyncio
import logging
import threading
from typing import Dict, Any

from app.sse.pod_spec_cache import cleanup_cache_background
from app.sse.sse_k6data import cleanup_job_metrics_buffers, resource_metrics_buffers

logger = logging.getLogger(__name__)


class CacheCleanupScheduler:
    """
    백그라운드 캐시 정리 스케줄러
    
    Features:
    - Pod spec 캐시 만료 항목 정리
    - 완료된 Job의 메트릭 버퍼 정리
    - 메모리 사용량 모니터링
    - 자동 정리 주기 관리
    """
    
    def __init__(self, cleanup_interval: int = 60, memory_check_interval: int = 300):
        """
        Args:
            cleanup_interval: 캐시 정리 주기 (초) - 기본 1분
            memory_check_interval: 메모리 체크 주기 (초) - 기본 5분
        """
        self.cleanup_interval = cleanup_interval
        self.memory_check_interval = memory_check_interval
        self.is_running = False
        self._cleanup_thread = None
        self._stop_event = threading.Event()
        
        # 통계 정보
        self.stats = {
            'total_cleanups': 0,
            'pod_cache_cleanups': 0,
            'metrics_buffer_cleanups': 0,
            'last_cleanup_time': None,
            'active_jobs': 0,
            'active_pods_cached': 0
        }
        
        logger.info(f"CacheCleanupScheduler initialized with cleanup_interval={cleanup_interval}s, "
                   f"memory_check_interval={memory_check_interval}s")
    
    def start(self):
        """백그라운드 정리 스케줄러 시작"""
        if self.is_running:
            logger.warning("Cache cleanup scheduler is already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(target=self._run_cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Cache cleanup scheduler started")
    
    def stop(self):
        """백그라운드 정리 스케줄러 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=10)
        
        logger.info("Cache cleanup scheduler stopped")
    
    def _run_cleanup_loop(self):
        """메인 정리 루프"""
        logger.info("Cache cleanup loop started")
        
        while self.is_running and not self._stop_event.is_set():
            try:
                self._perform_cleanup()
                
                # 주기적인 메모리 체크
                if self.stats['total_cleanups'] % (self.memory_check_interval // self.cleanup_interval) == 0:
                    self._check_memory_usage()
                
                # 다음 정리까지 대기
                self._stop_event.wait(timeout=self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
                # 에러 발생시 짧은 대기 후 재시도
                self._stop_event.wait(timeout=5)
    
    def _perform_cleanup(self):
        """캐시 정리 수행"""
        import time
        cleanup_start = time.time()
        
        try:
            # 1. Pod spec 캐시 정리
            pod_cache_cleaned = cleanup_cache_background()
            if pod_cache_cleaned > 0:
                self.stats['pod_cache_cleanups'] += pod_cache_cleaned
                logger.info(f"Cleaned up {pod_cache_cleaned} expired pod spec cache entries")
            
            # 2. 메트릭 버퍼 정리 (오래된 Job 자동 감지)
            metrics_cleaned = self._cleanup_old_metrics_buffers()
            if metrics_cleaned > 0:
                self.stats['metrics_buffer_cleanups'] += metrics_cleaned
                logger.info(f"Cleaned up {metrics_cleaned} old metrics buffers")
            
            # 3. 통계 업데이트
            self.stats['total_cleanups'] += 1
            self.stats['last_cleanup_time'] = time.time()
            self.stats['active_jobs'] = len(resource_metrics_buffers)
            
            # Pod 캐시 상태도 확인 (가능하면)
            try:
                from app.sse.pod_spec_cache import get_pod_spec_cache
                cache = get_pod_spec_cache()
                cache_status = cache.get_cache_status()
                self.stats['active_pods_cached'] = cache_status['active_entries']
            except Exception as e:
                logger.debug(f"Could not get pod cache status: {e}")
            
            cleanup_duration = time.time() - cleanup_start
            
            # 정기적으로 통계 로그
            if self.stats['total_cleanups'] % 10 == 0:  # 10번마다 (10분마다)
                logger.info(f"Cache cleanup stats: cleanups={self.stats['total_cleanups']}, "
                           f"pod_cache_cleaned={self.stats['pod_cache_cleanups']}, "
                           f"metrics_cleaned={self.stats['metrics_buffer_cleanups']}, "
                           f"active_jobs={self.stats['active_jobs']}, "
                           f"duration={cleanup_duration:.2f}s")
        
        except Exception as e:
            logger.error(f"Error performing cache cleanup: {e}")
    
    def _cleanup_old_metrics_buffers(self) -> int:
        """
        오래된 메트릭 버퍼들 정리
        
        기준:
        - 빈 버퍼 (Pod가 없는 Job)
        - 장기간 업데이트 없는 버퍼
        
        Returns:
            int: 정리된 Job 수
        """
        if not resource_metrics_buffers:
            return 0
        
        import time
        current_time = time.time()
        jobs_to_cleanup = []
        
        for job_name, job_buffers in resource_metrics_buffers.items():
            should_cleanup = False
            
            # 1. 빈 Job 버퍼
            if not job_buffers:
                should_cleanup = True
                logger.debug(f"Job {job_name} has empty buffers - marking for cleanup")
            
            # 2. 모든 Pod 버퍼가 비어있는 경우
            elif all(not pod_buffers for pod_buffers in job_buffers.values()):
                should_cleanup = True
                logger.debug(f"Job {job_name} has no active pod buffers - marking for cleanup")
            
            # 3. 장기간 업데이트 없는 경우 (30분)
            else:
                oldest_update = current_time
                for pod_name, pod_buffers in job_buffers.items():
                    for metric_type, buffer in pod_buffers.items():
                        if buffer.timestamps:
                            last_update = buffer.timestamps[-1].timestamp()
                            oldest_update = min(oldest_update, last_update)
                
                # 30분(1800초) 이상 업데이트 없으면 정리
                if current_time - oldest_update > 1800:
                    should_cleanup = True
                    logger.info(f"Job {job_name} has no updates for {(current_time - oldest_update):.0f}s - "
                               "marking for cleanup")
            
            if should_cleanup:
                jobs_to_cleanup.append(job_name)
        
        # 정리 실행
        cleaned_count = 0
        for job_name in jobs_to_cleanup:
            try:
                cleanup_job_metrics_buffers(job_name)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up job {job_name}: {e}")
        
        return cleaned_count
    
    def _check_memory_usage(self):
        """메모리 사용량 체크 및 경고"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # 메모리 사용량이 500MB 이상이면 경고
            if memory_mb > 500:
                logger.warning(f"High memory usage detected: {memory_mb:.1f}MB")
                logger.warning(f"Active jobs in buffers: {len(resource_metrics_buffers)}")
                
                # 강제 정리 고려 (1GB 이상)
                if memory_mb > 1024:
                    logger.warning("Memory usage over 1GB - forcing aggressive cleanup")
                    self._force_cleanup_old_buffers()
            
            else:
                logger.debug(f"Memory usage: {memory_mb:.1f}MB")
                
        except ImportError:
            logger.debug("psutil not available - skipping memory check")
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
    
    def _force_cleanup_old_buffers(self):
        """메모리 부족시 강제 정리"""
        import time
        current_time = time.time()
        
        # 15분 이상 된 버퍼들 강제 정리
        jobs_to_cleanup = []
        for job_name, job_buffers in list(resource_metrics_buffers.items()):
            for pod_name, pod_buffers in job_buffers.items():
                for metric_type, buffer in pod_buffers.items():
                    if buffer.timestamps:
                        last_update = buffer.timestamps[-1].timestamp()
                        if current_time - last_update > 900:  # 15분
                            jobs_to_cleanup.append(job_name)
                            break
                if job_name in jobs_to_cleanup:
                    break
        
        cleaned = 0
        for job_name in set(jobs_to_cleanup):  # 중복 제거
            cleanup_job_metrics_buffers(job_name)
            cleaned += 1
        
        if cleaned > 0:
            logger.warning(f"Force cleaned {cleaned} jobs due to high memory usage")
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 통계 정보 반환"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'cleanup_interval': self.cleanup_interval,
            'memory_check_interval': self.memory_check_interval
        }
    
    def force_cleanup(self) -> Dict[str, int]:
        """수동 정리 실행"""
        logger.info("Manual cache cleanup requested")
        
        pod_cleaned = cleanup_cache_background()
        metrics_cleaned = self._cleanup_old_metrics_buffers()
        
        result = {
            'pod_cache_cleaned': pod_cleaned,
            'metrics_buffers_cleaned': metrics_cleaned
        }
        
        logger.info(f"Manual cleanup completed: {result}")
        return result


# 글로벌 스케줄러 인스턴스
_cache_scheduler = None


def get_cache_scheduler() -> CacheCleanupScheduler:
    """캐시 정리 스케줄러 싱글톤 인스턴스 반환"""
    global _cache_scheduler
    if _cache_scheduler is None:
        _cache_scheduler = CacheCleanupScheduler()
    return _cache_scheduler


def start_cache_scheduler():
    """캐시 정리 스케줄러 시작"""
    scheduler = get_cache_scheduler()
    scheduler.start()


def stop_cache_scheduler():
    """캐시 정리 스케줄러 중지"""
    scheduler = get_cache_scheduler()
    scheduler.stop()