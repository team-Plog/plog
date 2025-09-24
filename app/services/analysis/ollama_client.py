"""
Ollama API 클라이언트 모듈

로컬 Ollama 서버와의 통신을 담당하며, AI 모델을 사용한 분석 요청을 처리합니다.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

import httpx


logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Ollama 클라이언트 설정"""
    model_name: str = ""
    base_url: str = ""
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout_seconds: int = 120

    @classmethod
    def from_settings(cls):
        """settings에서 설정값을 가져와서 OllamaConfig 생성"""
        from app.core.config import settings
        ai_config = settings.get_ai_config()
        return cls(
            model_name=ai_config['model_name'],
            base_url=ai_config['ollama_host'],
            temperature=ai_config['temperature'],
            max_tokens=ai_config['max_tokens'],
            timeout_seconds=ai_config['timeout_seconds']
        )


class OllamaClient:
    """Ollama API 클라이언트"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def _ensure_client(self):
        """HTTP 클라이언트 생성 (필요시)"""
        if self.client is None or self.client.is_closed:
            timeout = httpx.Timeout(self.config.timeout_seconds)
            self.client = httpx.AsyncClient(timeout=timeout)
    
    async def is_available(self) -> bool:
        """Ollama 서버 연결 가능 여부 확인"""
        try:
            await self._ensure_client()
            
            response = await self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                # 설정된 모델이 사용 가능한지 확인
                models = data.get("models", [])
                model_names = [model["name"] for model in models]
                
                # 모델명이 정확히 일치하거나 모델명이 포함된 경우를 찾음
                for model_name in model_names:
                    if self.config.model_name in model_name or model_name.startswith(self.config.model_name):
                        return True
                
                logger.warning(f"Model '{self.config.model_name}' not found. Available models: {model_names}")
                return len(models) > 0  # 다른 모델이라도 있으면 사용 가능
            else:
                logger.error(f"Ollama server returned status {response.status_code}")
                return False
                    
        except Exception as e:
            logger.error(f"Failed to check Ollama availability: {e}")
            return False
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 조회"""
        try:
            await self._ensure_client()
            
            response = await self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                # 모델 정보를 표준 형식으로 변환
                formatted_models = []
                for model in models:
                    formatted_models.append({
                        "name": model["name"],
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at"),
                        "digest": model.get("digest", ""),
                        "details": model.get("details", {})
                    })
                
                return formatted_models
            else:
                logger.error(f"Failed to get models: HTTP {response.status_code}")
                return []
                    
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    async def analyze_performance(
        self, 
        prompt: str, 
        analysis_type: str
    ) -> Dict[str, Any]:
        """
        성능 분석 수행
        
        Args:
            prompt: 분석용 프롬프트
            analysis_type: 분석 유형
            
        Returns:
            분석 결과 딕셔너리
        """
        
        try:
            await self._ensure_client()
            
            # Ollama API 요청 데이터 구성
            request_data = {
                "model": self.config.model_name,
                "prompt": prompt,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                },
                "stream": False  # 스트리밍 비활성화
            }
            
            logger.info(f"Sending analysis request to Ollama: {analysis_type}")
            
            response = await self.client.post(
                f"{self.config.base_url}/api/generate",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                if not response_text.strip():
                    logger.warning(f"Empty response from Ollama for {analysis_type}")
                    return {
                        "success": False,
                        "error": "Empty response from model",
                        "response": "",
                        "analysis_type": analysis_type
                    }
                
                # 성능 점수 추출 (단순화)
                performance_score = self._extract_performance_score(response_text)

                logger.info(f"Analysis completed for {analysis_type}, response length: {len(response_text)}")

                return {
                    "success": True,
                    "response": response_text,
                    "performance_score": performance_score,
                    "analysis_type": analysis_type
                }
            
            else:
                error_text = response.text
                logger.error(f"Ollama API error {response.status_code}: {error_text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}",
                    "response": "",
                    "analysis_type": analysis_type
                }
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout during analysis: {analysis_type}")
            return {
                "success": False,
                "error": f"Analysis timeout after {self.config.timeout_seconds} seconds",
                "response": "",
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            logger.error(f"Error during analysis {analysis_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "analysis_type": analysis_type
            }
    
    def _extract_performance_score(self, response_text: str) -> Optional[float]:
        """응답 텍스트에서 성능 점수 추출"""
        
        import re
        
        # 다양한 점수 패턴 검색
        score_patterns = [
            r"성능\s*점수[\s:]*(\d+(?:\.\d+)?)점?",
            r"점수[\s:]*(\d+(?:\.\d+)?)점?",
            r"평가[\s:]*(\d+(?:\.\d+)?)점?",
            r"(\d+(?:\.\d+)?)점?\s*/\s*100",
            r"(\d+(?:\.\d+)?)점?\s*\(\s*100점\s*만점\s*\)",
            r"전체\s*(?:성능|평가)\s*[\s:]*(\d+(?:\.\d+)?)점?"
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    # 점수가 0-100 범위에 있는지 확인
                    if 0 <= score <= 100:
                        return score
                    elif score > 100:
                        # 100보다 큰 경우 100으로 제한
                        return 100.0
                except (ValueError, IndexError):
                    continue
        
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Ollama 서버 헬스 체크"""
        
        try:
            await self._ensure_client()
            
            # 1. 서버 연결 확인
            response = await self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code != 200:
                return {
                    "status": "unhealthy",
                    "error": f"Server returned {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
            
            # 2. 설정된 모델 사용 가능 여부 확인
            models = await self.get_available_models()
            model_available = any(
                self.config.model_name in model["name"] or model["name"].startswith(self.config.model_name)
                for model in models
            )
            
            if not model_available:
                return {
                    "status": "degraded",
                    "warning": f"Configured model '{self.config.model_name}' not available",
                    "available_models": [m["name"] for m in models],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 3. 간단한 응답 테스트
            test_response = await self.analyze_performance(
                "간단히 '테스트 성공'이라고 답해주세요.", 
                "health_check"
            )
            
            if not test_response["success"]:
                return {
                    "status": "unhealthy", 
                    "error": f"Test query failed: {test_response['error']}",
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "status": "healthy",
                "model_name": self.config.model_name,
                "available_models": [m["name"] for m in models],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 전역 클라이언트 인스턴스 관리
_ollama_client: Optional[OllamaClient] = None


async def get_ollama_client(config: Optional[OllamaConfig] = None) -> OllamaClient:
    """
    Ollama 클라이언트 인스턴스 반환 (싱글톤)
    
    Args:
        config: Ollama 설정 (미지정시 기본값 사용)
        
    Returns:
        OllamaClient 인스턴스
    """
    
    global _ollama_client
    
    if _ollama_client is None:
        _ollama_client = OllamaClient(config)
        await _ollama_client._ensure_client()
    elif config and _ollama_client.config != config:
        # 설정이 변경된 경우 새 인스턴스 생성
        if _ollama_client.client and not _ollama_client.client.is_closed:
            await _ollama_client.client.aclose()
        _ollama_client = OllamaClient(config)
        await _ollama_client._ensure_client()
    
    return _ollama_client


async def close_ollama_client():
    """전역 Ollama 클라이언트 세션 종료"""
    
    global _ollama_client
    
    if _ollama_client and _ollama_client.client and not _ollama_client.client.is_closed:
        await _ollama_client.client.aclose()
        _ollama_client = None