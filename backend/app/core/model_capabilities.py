from pydantic import BaseModel
from typing import Optional, Dict

class ModelCapability(BaseModel):
    supports_temperature: bool = True
    supports_vision: bool = False
    supports_tools: bool = False
    supports_responses_api: bool = False # For new GPT-5 responses primitive
    max_output_tokens: Optional[int] = None
    api_type: str = "chat_completions" # chat_completions, responses

class ModelRegistry:
    _capabilities: Dict[str, ModelCapability] = {
        
        # GPT-5 family (use Responses API)  
        "gpt-5-nano": ModelCapability(
            supports_temperature=True,
            supports_vision=False,
            supports_tools=True,
            api_type="responses",
        ),
        "gpt-5-mini": ModelCapability(
            supports_temperature=True,
            supports_vision=False,
            supports_tools=True,
            api_type="responses",
        ),
        "gpt-5.1": ModelCapability(
            supports_temperature=True,
            supports_vision=True,
            supports_tools=True,
            api_type="responses",
        ),
        
    }
    
    _defaults = ModelCapability()

    @classmethod
    def get_capabilities(cls, model_id: str) -> ModelCapability:
        if not model_id:
            return cls._defaults

        if model_id in cls._capabilities:
            return cls._capabilities[model_id]

        if model_id.startswith("gpt-5"):
            return cls._capabilities.get("gpt-5-nano", cls._defaults)

        if model_id.startswith("o1"):
            return ModelCapability(supports_temperature=False, supports_tools=False, api_type="chat_completions")

        return cls._defaults
