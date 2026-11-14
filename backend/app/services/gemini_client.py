import os
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")

    @property
    def is_available(self) -> bool:
        return bool(self._client)

    async def generate_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None

        try:
            from google.genai import types
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini API generation failed: {e}")
            return None

gemini_client = GeminiClient()
