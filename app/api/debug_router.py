from fastapi import APIRouter
from typing import Dict, Any
import logging

from app.sse.pod_spec_cache import get_pod_spec_cache
from app.sse.sse_k6data import resource_metrics_buffers
from app.scheduler.cache_cleanup_scheduler import get_cache_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/cache/status")
async def get_cache_status() -> Dict[str, Any]:
    """
    캐시 시스템 전체 상태 조회
    
    Returns:
        Dict containing cache status information
    """
    try:
        # 1. Pod Spec 캐시 상태
        pod_cache = get_pod_spec_cache()
        pod_cache_status = pod_cache.get_cache_status()
        
        # 2. 메트릭 버퍼 상태
        metrics_buffer_status = {
            'active_jobs': len(resource_metrics_buffers),
            'jobs': {}
        }
        
        for job_name, job_buffers in resource_metrics_buffers.items():
            pod_count = len(job_buffers)
            total_buffers = sum(len(pod_buffers) for pod_buffers in job_buffers.values())
            
            # 각 버퍼의 상태 요약 (service_type 정보도 포함)
            buffer_states = []
            for pod_name, pod_buffers in job_buffers.items():
                for metric_type, buffer in pod_buffers.items():
                    state = buffer.get_current_state()
                    buffer_states.append({
                        'pod': pod_name,
                        'metric': metric_type,
                        'current_value': state['current_value'],
                        'is_predicted': state['is_predicted'],
                        'prediction_streak': state['prediction_streak'],
                        'confidence': state['confidence'],
                        'buffer_size': state['buffer_size']
                    })
            
            metrics_buffer_status['jobs'][job_name] = {
                'pod_count': pod_count,
                'total_buffers': total_buffers,
                'buffer_states': buffer_states,
                'note': 'Resources now returned as flat array instead of hierarchical structure'
            }
        
        # 3. 캐시 정리 스케줄러 상태
        scheduler = get_cache_scheduler()
        scheduler_stats = scheduler.get_stats()
        
        return {
            'pod_spec_cache': pod_cache_status,
            'metrics_buffers': metrics_buffer_status,
            'cleanup_scheduler': scheduler_stats,
            'system_status': 'healthy'
        }
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return {
            'error': str(e),
            'system_status': 'error'
        }


@router.post("/cache/cleanup")
async def force_cache_cleanup() -> Dict[str, Any]:
    """
    수동 캐시 정리 실행
    
    Returns:
        Dict containing cleanup results
    """
    try:
        scheduler = get_cache_scheduler()
        cleanup_results = scheduler.force_cleanup()
        
        return {
            'success': True,
            'cleanup_results': cleanup_results,
            'message': 'Cache cleanup completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Error during manual cache cleanup: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Cache cleanup failed'
        }


@router.get("/cache/pod-specs")
async def get_pod_specs_detail() -> Dict[str, Any]:
    """
    Pod Spec 캐시 상세 정보 조회
    
    Returns:
        Dict containing detailed pod spec cache information
    """
    try:
        pod_cache = get_pod_spec_cache()
        status = pod_cache.get_cache_status()
        
        # 캐시된 Pod들의 상세 정보
        detailed_cache = {}
        for pod_name in status['cached_pods']:
            spec = pod_cache.cache.get(pod_name)
            timestamp = pod_cache.timestamps.get(pod_name)
            
            if spec and timestamp:
                import time
                age_seconds = time.time() - timestamp
                
                detailed_cache[pod_name] = {
                    'cpu_limit_millicores': spec.get('cpu_limit_millicores'),
                    'memory_limit_mb': spec.get('memory_limit_mb'),
                    'cpu_request_millicores': spec.get('cpu_request_millicores'),
                    'memory_request_mb': spec.get('memory_request_mb'),
                    'cached_timestamp': timestamp,
                    'age_seconds': round(age_seconds, 1),
                    'is_expired': age_seconds > pod_cache.ttl
                }
        
        return {
            'cache_summary': status,
            'detailed_cache': detailed_cache
        }
        
    except Exception as e:
        logger.error(f"Error getting pod specs detail: {e}")
        return {
            'error': str(e)
        }


@router.get("/cache/metrics-buffers/{job_name}")
async def get_job_metrics_detail(job_name: str) -> Dict[str, Any]:
    """
    특정 Job의 메트릭 버퍼 상세 정보 조회
    
    Args:
        job_name: 조회할 Job 이름
        
    Returns:
        Dict containing detailed metrics buffer information for the job
    """
    try:
        if job_name not in resource_metrics_buffers:
            return {
                'error': f"Job '{job_name}' not found in metrics buffers",
                'available_jobs': list(resource_metrics_buffers.keys())
            }
        
        job_buffers = resource_metrics_buffers[job_name]
        
        detailed_info = {
            'job_name': job_name,
            'pod_count': len(job_buffers),
            'pods': {}
        }
        
        for pod_name, pod_buffers in job_buffers.items():
            pod_info = {
                'metric_count': len(pod_buffers),
                'metrics': {}
            }
            
            for metric_type, buffer in pod_buffers.items():
                state = buffer.get_current_state()
                
                # 버퍼 히스토리 정보
                history = []
                for i, (value, timestamp, is_pred, confidence) in enumerate(zip(
                    buffer.values, buffer.timestamps, buffer.is_predicted, buffer.confidence
                )):
                    history.append({
                        'index': i,
                        'value': round(float(value), 2),
                        'timestamp': timestamp.isoformat(),
                        'is_predicted': is_pred,
                        'confidence': round(float(confidence), 3)
                    })
                
                pod_info['metrics'][metric_type] = {
                    'current_state': state,
                    'history': history[-5:] if len(history) > 5 else history,  # 최근 5개만
                    'total_history_count': len(history)
                }
            
            detailed_info['pods'][pod_name] = pod_info
        
        return detailed_info
        
    except Exception as e:
        logger.error(f"Error getting job metrics detail for {job_name}: {e}")
        return {
            'error': str(e)
        }


@router.get("/resources/structure/{job_name}")
async def get_resources_structure_preview(job_name: str) -> Dict[str, Any]:
    """
    새로운 Resources 구조 미리보기
    
    Args:
        job_name: 조회할 Job 이름
        
    Returns:
        Dict containing new resources structure preview
    """
    try:
        from app.sse.sse_k6data import collect_resource_metrics, get_job_pods_with_service_types
        
        # 1. DB에서 Pod 정보 조회
        pod_info_list = get_job_pods_with_service_types(job_name)
        
        # 2. 실제 메트릭 수집
        resource_metrics = collect_resource_metrics(job_name)
        
        return {
            'job_name': job_name,
            'pod_discovery': {
                'found_pods': len(pod_info_list),
                'pods_info': pod_info_list
            },
            'new_structure_preview': {
                'format': 'resources: [...]  # Direct array instead of {overall, servers}',
                'sample_data': resource_metrics[:2] if resource_metrics else [],
                'total_pods': len(resource_metrics) if resource_metrics else 0
            },
            'structure_comparison': {
                'old_format': {
                    'resources': {
                        'overall': '{ avg CPU/Memory }',
                        'servers': '[ individual pods ]',
                        'prediction_info': '{ aggregated stats }'
                    }
                },
                'new_format': {
                    'resources': [
                        {
                            'pod_name': 'example',
                            'service_type': 'SERVER',  # From DB
                            'cpu_usage_percent': 30.5,
                            'memory_usage_percent': 52.1,
                            '...': 'other fields'
                        }
                    ]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting resources structure for {job_name}: {e}")
        return {
            'error': str(e)
        }