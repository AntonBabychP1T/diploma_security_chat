from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ProviderResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[Any]] = None
    meta_data: Dict[str, Any] = {}

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], options: Optional[Dict[str, Any]] = None) -> ProviderResponse:
        """
        Generates a response from the LLM.
        
        Args:
            messages: List of messages [{"role": "user", "content": "..."}]
            options: Additional provider-specific options
            
        Returns:
            ProviderResponse with content and metadata
        """
        pass
