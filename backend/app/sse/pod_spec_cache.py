import time
import logging
from typing import Dict, Optional, List
from k8s.resource_service import ResourceService

logger = logging.getLogger(__name__)


class PodSpecCache:
    """
    Pod 리소스 스펙 캐싱 클래스
    
    Pod의 CPU/Memory limit 정보는 자주 변하지 않으므로 캐싱하여
    Kubernetes API 호출을 최소화합니다.
    
    Features:
    - TTL 기반 캐싱 (기본 5분)
    - 자동 만료 관리
    - 수동 캐시 무효화 지원
    - 백그라운드 정리
    """
    
    def __init__(self, ttl: int = 300):
        """
        Args:
            ttl: Time To Live in seconds (기본값: 300초 = 5분)
        """
        self.cache: Dict[str, Dict[str, float]] = {}
        self.timestamps: Dict[str, float] = {}
        self.ttl = ttl
        self.resource_service = ResourceService()
        logger.info(f"PodSpecCache initialized with TTL={ttl}s")
    
    def get_pod_spec(self, pod_name: str) -> Optional[Dict[str, float]]:
        """
        Pod 리소스 스펙 조회 (캐시 우선)
        
        Args:
            pod_name: Pod 이름
            
        Returns:
            Dict containing:
            - cpu_request_millicores: CPU 요청량 (millicores)
            - cpu_limit_millicores: CPU 제한량 (millicores)
            - memory_request_mb: Memory 요청량 (MB)
            - memory_limit_mb: Memory 제한량 (MB)
        """
        current_time = time.time()
        
        # 캐시에 있고 TTL 내이면 캐시 반환
        if (pod_name in self.cache and 
            pod_name in self.timestamps and
            current_time - self.timestamps[pod_name] < self.ttl):
            
            logger.debug(f"Pod spec cache hit for {pod_name}")
            return self.cache[pod_name]
        
        # 캐시 미스 또는 만료: Kubernetes API 호출
        logger.info(f"Pod spec cache miss for {pod_name}, querying Kubernetes API")
        spec = self.resource_service.get_pod_aggregated_resources(pod_name)
        
        if spec:
            self.cache[pod_name] = spec
            self.timestamps[pod_name] = current_time
            logger.info(f"Pod spec cached for {pod_name}: CPU={spec.get('cpu_limit_millicores')}m, "
                       f"Memory={spec.get('memory_limit_mb')}MB")
        else:
            logger.warning(f"Failed to get pod spec for {pod_name}")
        
        return spec
    
    def invalidate_pod(self, pod_name: str) -> bool:
        """
        특정 Pod의 캐시 무효화
        
        Pod 재시작/업데이트시 수동으로 호출
        
        Args:
            pod_name: 무효화할 Pod 이름
            
        Returns:
            bool: 캐시가 존재했고 삭제되었는지 여부
        """
        was_cached = pod_name in self.cache
        
        if was_cached:
            del self.cache[pod_name]
            del self.timestamps[pod_name]
            logger.info(f"Pod spec cache invalidated for {pod_name}")
        
        return was_cached
    
    def cleanup_expired(self) -> int:
        """
        만료된 캐시 항목들 정리
        
        Returns:
            int: 정리된 캐시 항목 수
        """
        current_time = time.time()
        expired_pods = [
            pod for pod, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        
        cleanup_count = 0
        for pod in expired_pods:
            if self.invalidate_pod(pod):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired pod spec cache entries")
        
        return cleanup_count
    
    def preload_job_pods(self, job_name: str, pod_names: List[str]) -> int:
        """
        Job 시작시 관련 Pod들의 스펙 미리 캐싱
        
        Args:
            job_name: Job 이름 (로깅용)
            pod_names: 캐싱할 Pod 이름 목록
            
        Returns:
            int: 성공적으로 캐싱된 Pod 수
        """
        logger.info(f"Preloading pod specs for job {job_name}: {pod_names}")
        
        success_count = 0
        for pod_name in pod_names:
            spec = self.get_pod_spec(pod_name)
            if spec:
                success_count += 1
        
        logger.info(f"Preloaded {success_count}/{len(pod_names)} pod specs for job {job_name}")
        return success_count
    
    def get_cache_status(self) -> Dict[str, any]:
        """
        캐시 상태 정보 반환 (디버깅/모니터링용)
        
        Returns:
            Dict containing cache statistics
        """
        current_time = time.time()
        active_entries = sum(1 for timestamp in self.timestamps.values() 
                           if current_time - timestamp < self.ttl)
        
        return {
            'total_entries': len(self.cache),
            'active_entries': active_entries,
            'expired_entries': len(self.cache) - active_entries,
            'ttl_seconds': self.ttl,
            'oldest_entry_age': current_time - min(self.timestamps.values()) if self.timestamps else 0,
            'cached_pods': list(self.cache.keys())
        }


# 글로벌 싱글톤 인스턴스
_pod_spec_cache = None


def get_pod_spec_cache() -> PodSpecCache:
    """
    PodSpecCache 싱글톤 인스턴스 반환
    
    Returns:
        PodSpecCache: 글로벌 캐시 인스턴스
    """
    global _pod_spec_cache
    if _pod_spec_cache is None:
        _pod_spec_cache = PodSpecCache()
    return _pod_spec_cache


def cleanup_cache_background() -> int:
    """
    백그라운드에서 호출할 캐시 정리 함수
    
    Returns:
        int: 정리된 캐시 항목 수
    """
    cache = get_pod_spec_cache()
    return cache.cleanup_expired()