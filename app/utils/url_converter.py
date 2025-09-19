import re
from urllib.parse import urlparse, urlunparse
from typing import Dict, Optional
from app.core.config import settings


def is_localhost_url(url: str) -> bool:
    """
    URL이 localhost 패턴인지 확인

    Args:
        url: 확인할 URL

    Returns:
        bool: localhost 패턴이면 True
    """
    parsed = urlparse(url.lower())
    return parsed.hostname in ['localhost', '127.0.0.1']


def detect_nodeport_pattern(url: str) -> Optional[Dict[str, str]]:
    """
    URL에서 NodePort 패턴을 감지하고 정보 추출

    Args:
        url: 분석할 URL

    Returns:
        Dict: 감지된 패턴 정보 또는 None
    """
    if not is_localhost_url(url):
        return None

    parsed = urlparse(url)
    if not parsed.port:
        return None

    return {
        'hostname': parsed.hostname,
        'port': str(parsed.port),
        'scheme': parsed.scheme,
        'path': parsed.path
    }


def convert_localhost_to_service_url(
    base_url: str,
    service_name: str = None,
    service_port: int = None,
    namespace: str = None
) -> str:
    """
    localhost URL을 Kubernetes service URL로 변환

    Args:
        base_url: 변환할 기본 URL
        service_name: 서비스 이름 (없으면 자동 감지 시도)
        service_port: 서비스 포트 (없으면 현재 포트 사용)
        namespace: 네임스페이스 (없으면 설정값 사용)

    Returns:
        str: 변환된 URL
    """
    if not is_localhost_url(base_url):
        return base_url

    parsed = urlparse(base_url)

    # 기본값 설정
    target_namespace = namespace or getattr(settings, 'KUBERNETES_TEST_NAMESPACE', 'test')
    target_port = service_port or parsed.port

    if not service_name:
        # service_name을 추정할 수 없으면 원본 반환
        return base_url

    # 새로운 hostname 생성
    new_hostname = f"{service_name}.{target_namespace}.svc.cluster.local"

    # URL 재구성
    new_netloc = f"{new_hostname}:{target_port}" if target_port else new_hostname

    return urlunparse((
        parsed.scheme,
        new_netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def convert_url_with_mapping(
    base_url: str,
    conversion_mappings: Dict[str, Dict[str, str]] = None
) -> str:
    """
    변환 매핑 정보를 사용하여 URL 변환 (server_pod_scheduler 호환)

    Args:
        base_url: 변환할 URL
        conversion_mappings: 변환 매핑 정보
            예: {"http://localhost:30080/swagger-ui": {"service_name": "app", "service_port": "8080"}}

    Returns:
        str: 변환된 URL
    """
    if not conversion_mappings:
        return base_url

    # 정확한 매칭을 위해 base URL 정규화
    parsed_base = urlparse(base_url)
    base_key = f"{parsed_base.scheme}://{parsed_base.netloc}"

    # 매핑에서 변환 정보 찾기
    conversion_info = None
    for mapping_url, info in conversion_mappings.items():
        parsed_mapping = urlparse(mapping_url)
        mapping_key = f"{parsed_mapping.scheme}://{parsed_mapping.netloc}"
        if base_key == mapping_key:
            conversion_info = info
            break

    if not conversion_info:
        return base_url

    # 변환 수행
    service_name = conversion_info.get('service_name')
    service_port = conversion_info.get('service_port')
    namespace = conversion_info.get('namespace', getattr(settings, 'KUBERNETES_TEST_NAMESPACE', 'test'))

    if not service_name:
        return base_url

    return convert_localhost_to_service_url(
        base_url=base_url,
        service_name=service_name,
        service_port=int(service_port) if service_port else None,
        namespace=namespace
    )


def create_nodeport_conversion_mapping(
    swagger_url: str,
    service_name: str,
    service_port: int,
    node_port: int,
    namespace: str = None
) -> Dict[str, Dict[str, str]]:
    """
    NodePort 변환 매핑 생성 (server_pod_scheduler 호환)

    Args:
        swagger_url: Swagger URL
        service_name: 서비스 이름
        service_port: 서비스 포트
        node_port: NodePort 포트
        namespace: 네임스페이스

    Returns:
        Dict: 변환 매핑 정보
    """
    target_namespace = namespace or getattr(settings, 'KUBERNETES_TEST_NAMESPACE', 'test')

    return {
        swagger_url: {
            'service_name': service_name,
            'service_port': str(service_port),
            'node_port': str(node_port),
            'namespace': target_namespace
        }
    }


def extract_service_info_from_url(url: str) -> Optional[Dict[str, str]]:
    """
    URL에서 서비스 정보 추출 시도

    Args:
        url: 분석할 URL

    Returns:
        Dict: 추출된 서비스 정보 또는 None
    """
    parsed = urlparse(url)

    # Kubernetes service URL 패턴 확인
    if '.svc.cluster.local' in parsed.hostname:
        parts = parsed.hostname.split('.')
        if len(parts) >= 3:
            return {
                'service_name': parts[0],
                'namespace': parts[1],
                'port': str(parsed.port) if parsed.port else '80'
            }

    return None

def is_same_origin_base_url(url1: str, url2: str) -> bool:
    parse_url1 = urlparse(url1)
    parse_url2 = urlparse(url2)

    if parse_url1.scheme != parse_url2.scheme:
        return False

    if parse_url1.netloc != parse_url2.netloc:
        return False

    return True

