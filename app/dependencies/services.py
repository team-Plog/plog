from functools import lru_cache

from k8s.resource_service import ResourceService

@lru_cache()
def get_resource_service() -> ResourceService:
    return ResourceService()