import asyncio
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.core.config import get_settings
from .base import LLMProvider, ProviderResponse

settings = get_settings()

class GeminiProvider(LLMProvider):
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.default_model = "gemini-2.5-flash"

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        gemini_contents = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            if m.get("role") == "system":
                # Gemini doesn't strictly have system role in chat history the same way
                # We can prepend it to the first user message or set it as system_instruction (if using new API)
                # For simplicity, if it's system, we treat it as user instruction or ignore if pure chat
                # Better: Prepend to next user message? 
                # Current simple approach: Treat as user with distinct text
                role = "user"
            
            parts = []
            content = m.get("content", "")
            
            if isinstance(content, str):
                parts.append({"text": content})
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item.get("text", "")})
                    elif item.get("type") == "image_url":
                        # Parse base64
                        url = item.get("image_url", {}).get("url", "")
                        # data:image/png;base64,....
                        if "," in url:
                            header, data = url.split(",", 1)
                            mime_type = item.get("mime_type", "image/jpeg") # Default or extract from header
                            if ";base64" in header:
                                mime_part = header.replace("data:", "").replace(";base64", "")
                                if mime_part: mime_type = mime_part
                        else:
                            data = url
                            mime_type = item.get("mime_type", "image/jpeg")
                            
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": data
                            }
                        })
            
            if parts:
                gemini_contents.append({"role": role, "parts": parts})
        
        return gemini_contents

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        options = options or {}
        model_name = options.get("model", self.default_model)
        
        # Resolve aliases
        alias_map = {
            "gemini-2.5-flash": "models/gemini-2.5-flash",
            "gemini-2.5-flash-lite": "models/gemini-2.5-flash-lite",
        }
        model_id = alias_map.get(model_name, model_name)
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        contents = self._convert_messages(messages)

        def _generate_sync():
            model = genai.GenerativeModel(model_id)
            # system_instruction could be passed here if we parsed it out
            return model.generate_content(contents)

        try:
            response = await asyncio.to_thread(_generate_sync)
            text = response.text or ""
            
            # Extract usage if avail
            usage_data = {}
            if hasattr(response, "usage_metadata"):
                u = response.usage_metadata
                usage_data = {
                    "prompt_token_count": u.prompt_token_count,
                    "candidates_token_count": u.candidates_token_count,
                    "total_token_count": u.total_token_count
                }

            return ProviderResponse(
                content=text,
                meta_data={
                    "provider": "gemini",
                    "model": model_name,
                    "usage": usage_data
                }
            )
        except Exception as e:
            print(f"Gemini Provider Error: {e}")
            raise e

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ):
        options = options or {}
        model_name = options.get("model", self.default_model)
        
        alias_map = {
            "gemini-2.5-flash": "models/gemini-2.5-flash",
            "gemini-2.5-flash-lite": "models/gemini-2.5-flash-lite",
        }
        model_id = alias_map.get(model_name, model_name)
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        contents = self._convert_messages(messages)

        # Gemini SDK generate_content(stream=True) returns a synchronous iterator or async?
        # The python SDK is sync mostly, but has async support in beta? 
        # Standard approach is to use run_in_executor for the sync calls.
        # But for streaming, we need an async generator.
        
        model = genai.GenerativeModel(model_id)
        
        # We'll creating a mock response class to mimic OpenAI structure for the ChatService
        class MockChoice:
            def __init__(self, content):
                self.delta = type('obj', (object,), {'content': content})

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(content)]

        async def generator():
            # Run the stream request in thread
            response_stream = await asyncio.to_thread(model.generate_content, contents, stream=True)
            
            # response_stream is a sync iterator. We can iterate it.
            for chunk in response_stream:
                if chunk.text:
                    yield MockChunk(chunk.text)
                    # Yield slightly to event loop
                    await asyncio.sleep(0)

        return generator()
