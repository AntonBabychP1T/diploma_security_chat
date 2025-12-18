from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

class LLMOptions(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(None, gt=0)
    timeout: Optional[float] = Field(None, gt=0.0)
    stream: bool = False
    
    # Tooling
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    
    # Advanced
    previous_response_id: Optional[str] = None
    tool_runner: Optional[Any] = None # Helper callable, not always serializable
    
    # Internal flags
    _tool_calls_as_dict: bool = False

    class Config:
        extra = "ignore"
