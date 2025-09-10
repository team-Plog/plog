import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """AI 모델 제공자"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"


class ModelCapability(str, Enum):
    """모델 기능"""
    TEXT_GENERATION = "text_generation"
    CODE_ANALYSIS = "code_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    COMPARISON = "comparison"


@dataclass
class ModelInfo:
    """모델 정보"""
    name: str
    provider: ModelProvider
    display_name: str
    description: str
    capabilities: List[ModelCapability]
    max_tokens: int
    temperature_range: tuple  # (min, max)
    is_available: bool = False
    last_checked: Optional[datetime] = None
    performance_metrics: Optional[Dict[str, float]] = None


class ModelRegistry:
    """모델 레지스트리 - 사용 가능한 모델 관리"""
    
    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """기본 모델들 등록"""
        
        # Ollama 모델들
        ollama_models = [
            ModelInfo(
                name="llama3.1:8b",
                provider=ModelProvider.OLLAMA,
                display_name="Llama 3.1 8B",
                description="메타의 Llama 3.1 8B 모델 - 성능 분석에 적합",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.PERFORMANCE_ANALYSIS,
                    ModelCapability.COMPARISON
                ],
                max_tokens=4096,
                temperature_range=(0.0, 1.0)
            ),
            ModelInfo(
                name="llama3.1:13b",
                provider=ModelProvider.OLLAMA,
                display_name="Llama 3.1 13B",
                description="더 큰 모델로 더 정교한 분석 가능",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.PERFORMANCE_ANALYSIS,
                    ModelCapability.COMPARISON
                ],
                max_tokens=4096,
                temperature_range=(0.0, 1.0)
            ),
            ModelInfo(
                name="codellama:7b",
                provider=ModelProvider.OLLAMA,
                display_name="Code Llama 7B",
                description="코드 분석에 특화된 모델",
                capabilities=[
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.PERFORMANCE_ANALYSIS
                ],
                max_tokens=2048,
                temperature_range=(0.0, 0.5)
            ),
            ModelInfo(
                name="mistral:7b",
                provider=ModelProvider.OLLAMA,
                display_name="Mistral 7B",
                description="빠른 응답과 효율적인 분석",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.PERFORMANCE_ANALYSIS
                ],
                max_tokens=8192,
                temperature_range=(0.0, 1.0)
            )
        ]
        
        for model in ollama_models:
            self._models[model.name] = model
    
    def register_model(self, model_info: ModelInfo):
        """새로운 모델 등록"""
        self._models[model_info.name] = model_info
        logger.info(f"Registered model: {model_info.name}")
    
    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        """모델 정보 조회"""
        return self._models.get(model_name)
    
    def list_models(
        self, 
        provider: Optional[ModelProvider] = None,
        capability: Optional[ModelCapability] = None,
        available_only: bool = False
    ) -> List[ModelInfo]:
        """모델 목록 조회"""
        models = list(self._models.values())
        
        # 제공자 필터
        if provider:
            models = [m for m in models if m.provider == provider]
        
        # 기능 필터
        if capability:
            models = [m for m in models if capability in m.capabilities]
        
        # 사용 가능 여부 필터
        if available_only:
            models = [m for m in models if m.is_available]
        
        return models
    
    def update_availability(self, model_name: str, is_available: bool, performance_metrics: Dict[str, float] = None):
        """모델 사용 가능 여부 및 성능 메트릭 업데이트"""
        if model_name in self._models:
            self._models[model_name].is_available = is_available
            self._models[model_name].last_checked = datetime.now()
            if performance_metrics:
                self._models[model_name].performance_metrics = performance_metrics
    
    def get_recommended_model(
        self, 
        capability: ModelCapability,
        prefer_fast: bool = False,
        prefer_quality: bool = False
    ) -> Optional[ModelInfo]:
        """권장 모델 선택"""
        
        # 해당 기능을 지원하는 사용 가능한 모델들
        available_models = [
            m for m in self._models.values()
            if capability in m.capabilities and m.is_available
        ]
        
        if not available_models:
            return None
        
        # 속도 우선
        if prefer_fast:
            # 작은 모델 우선 (7b > 8b > 13b)
            available_models.sort(key=lambda m: (
                0 if "7b" in m.name.lower() else
                1 if "8b" in m.name.lower() else
                2 if "13b" in m.name.lower() else 3
            ))
        
        # 품질 우선
        elif prefer_quality:
            # 큰 모델 우선 (13b > 8b > 7b)
            available_models.sort(key=lambda m: (
                0 if "13b" in m.name.lower() else
                1 if "8b" in m.name.lower() else
                2 if "7b" in m.name.lower() else 3
            ))
        
        # 성능 메트릭 기반 정렬 (있는 경우)
        else:
            available_models.sort(key=lambda m: (
                -(m.performance_metrics or {}).get("quality_score", 0.5),
                (m.performance_metrics or {}).get("response_time", 999)
            ))
        
        return available_models[0]


class ModelSelector:
    """모델 선택 로직"""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
    
    async def select_optimal_model(
        self,
        analysis_type: str,
        data_size: int = 0,
        priority: str = "balanced"  # "speed", "quality", "balanced"
    ) -> Optional[ModelInfo]:
        """분석 유형과 우선순위에 따른 최적 모델 선택"""
        
        # 분석 유형별 필요한 기능 매핑
        capability_mapping = {
            "comprehensive": ModelCapability.PERFORMANCE_ANALYSIS,
            "response_time": ModelCapability.PERFORMANCE_ANALYSIS,
            "tps": ModelCapability.PERFORMANCE_ANALYSIS,
            "error_rate": ModelCapability.PERFORMANCE_ANALYSIS,
            "resource_usage": ModelCapability.PERFORMANCE_ANALYSIS,
            "comparison": ModelCapability.COMPARISON,
            "code_analysis": ModelCapability.CODE_ANALYSIS
        }
        
        required_capability = capability_mapping.get(analysis_type, ModelCapability.TEXT_GENERATION)
        
        # 우선순위에 따른 모델 선택
        if priority == "speed":
            return self.registry.get_recommended_model(required_capability, prefer_fast=True)
        elif priority == "quality":
            return self.registry.get_recommended_model(required_capability, prefer_quality=True)
        else:  # balanced
            # 데이터 크기에 따른 적응적 선택
            if data_size > 10000:  # 큰 데이터는 큰 모델
                return self.registry.get_recommended_model(required_capability, prefer_quality=True)
            else:  # 작은 데이터는 빠른 모델
                return self.registry.get_recommended_model(required_capability, prefer_fast=True)


class ModelConfiguration(BaseModel):
    """모델 설정"""
    model_name: str
    provider: ModelProvider
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout_seconds: int = 120
    custom_parameters: Dict[str, Any] = {}
    
    class Config:
        use_enum_values = True


class ModelManager:
    """모델 관리자 - 모델 선택, 설정, 성능 모니터링"""
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.selector = ModelSelector(self.registry)
        self._performance_history: List[Dict[str, Any]] = []
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 반환"""
        models = self.registry.list_models()
        
        # 모델 상태 체크 (Ollama만 체크)
        await self._check_model_availability()
        
        return [
            {
                "name": model.name,
                "provider": model.provider.value,
                "display_name": model.display_name,
                "description": model.description,
                "capabilities": [c.value for c in model.capabilities],
                "max_tokens": model.max_tokens,
                "is_available": model.is_available,
                "last_checked": model.last_checked.isoformat() if model.last_checked else None,
                "performance_score": (model.performance_metrics or {}).get("quality_score", 0.0)
            }
            for model in models
        ]
    
    async def select_model_for_analysis(
        self,
        analysis_type: str,
        data_complexity: str = "medium",  # "low", "medium", "high"
        user_preference: str = "balanced"  # "speed", "quality", "balanced"
    ) -> Optional[ModelConfiguration]:
        """분석을 위한 최적 모델 선택 및 설정"""
        
        # 데이터 복잡도를 크기로 변환
        complexity_to_size = {
            "low": 1000,
            "medium": 5000,
            "high": 15000
        }
        
        estimated_size = complexity_to_size.get(data_complexity, 5000)
        
        # 최적 모델 선택
        selected_model = await self.selector.select_optimal_model(
            analysis_type=analysis_type,
            data_size=estimated_size,
            priority=user_preference
        )
        
        if not selected_model:
            logger.warning(f"No suitable model found for {analysis_type}")
            return None
        
        # 모델 설정 생성
        config = ModelConfiguration(
            model_name=selected_model.name,
            provider=selected_model.provider,
            temperature=0.05 if analysis_type == "comparison" else 0.1,  # 비교 분석은 더 일관성 있게
            max_tokens=min(selected_model.max_tokens, 3000),  # 안전한 토큰 수
            timeout_seconds=180 if "13b" in selected_model.name else 120  # 큰 모델은 더 긴 타임아웃
        )
        
        logger.info(f"Selected model {selected_model.name} for {analysis_type} analysis")
        return config
    
    async def _check_model_availability(self):
        """모델 사용 가능 여부 확인 (Ollama만)"""
        try:
            from .ollama_client import get_ollama_client
            
            ollama_client = await get_ollama_client()
            if await ollama_client.is_available():
                ollama_models = await ollama_client.list_models()
                available_model_names = [
                    model.get("name", "") for model in ollama_models.get("models", [])
                ]
                
                # Ollama 모델들의 사용 가능 여부 업데이트
                for model_name, model_info in self.registry._models.items():
                    if model_info.provider == ModelProvider.OLLAMA:
                        is_available = model_name in available_model_names
                        self.registry.update_availability(model_name, is_available)
            
        except Exception as e:
            logger.warning(f"Failed to check Ollama model availability: {e}")
            # 모든 Ollama 모델을 사용 불가능으로 마크
            for model_name, model_info in self.registry._models.items():
                if model_info.provider == ModelProvider.OLLAMA:
                    self.registry.update_availability(model_name, False)
    
    def record_performance(
        self,
        model_name: str,
        analysis_type: str,
        duration_ms: int,
        quality_score: float,
        success: bool
    ):
        """모델 성능 기록"""
        
        performance_record = {
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "analysis_type": analysis_type,
            "duration_ms": duration_ms,
            "quality_score": quality_score,
            "success": success
        }
        
        self._performance_history.append(performance_record)
        
        # 최근 10개 기록만 유지
        self._performance_history = self._performance_history[-10:]
        
        # 모델의 평균 성능 메트릭 업데이트
        model_records = [
            r for r in self._performance_history
            if r["model_name"] == model_name and r["success"]
        ]
        
        if model_records:
            avg_duration = sum(r["duration_ms"] for r in model_records) / len(model_records)
            avg_quality = sum(r["quality_score"] for r in model_records) / len(model_records)
            
            self.registry.update_availability(
                model_name,
                True,
                {
                    "quality_score": avg_quality,
                    "response_time": avg_duration,
                    "success_rate": len(model_records) / len([
                        r for r in self._performance_history if r["model_name"] == model_name
                    ])
                }
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        if not self._performance_history:
            return {"total_analyses": 0, "models": {}}
        
        stats = {"total_analyses": len(self._performance_history), "models": {}}
        
        for record in self._performance_history:
            model_name = record["model_name"]
            if model_name not in stats["models"]:
                stats["models"][model_name] = {
                    "total_uses": 0,
                    "success_rate": 0.0,
                    "avg_duration_ms": 0.0,
                    "avg_quality_score": 0.0
                }
            
            model_stats = stats["models"][model_name]
            model_records = [r for r in self._performance_history if r["model_name"] == model_name]
            successful_records = [r for r in model_records if r["success"]]
            
            model_stats["total_uses"] = len(model_records)
            model_stats["success_rate"] = len(successful_records) / len(model_records) if model_records else 0
            
            if successful_records:
                model_stats["avg_duration_ms"] = sum(r["duration_ms"] for r in successful_records) / len(successful_records)
                model_stats["avg_quality_score"] = sum(r["quality_score"] for r in successful_records) / len(successful_records)
        
        return stats


# 전역 모델 매니저 인스턴스
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """모델 매니저 싱글톤 인스턴스 반환"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager