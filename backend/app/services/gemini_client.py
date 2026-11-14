import os
import json
import time
import asyncio
import hashlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Client wrapper for Google Gemini 2.0 Flash API using the google-genai SDK.
    Provides rate limiting (15 RPM), response caching, exponential backoff retries,
    and structured JSON generation with fallback capabilities.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")
        self._client = None
        self._last_request_time = 0.0
        self._min_interval = 4.0  # 15 requests per minute limit
        self._rate_limit_lock = asyncio.Lock()
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl = 300.0  # 5 minutes cache TTL
        self._init_client()

    def _init_client(self):
        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key.strip())
                logger.info("Google GenAI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")
                self._client = None
        else:
            self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _get_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        # Evict old entries if cache grows large
        if len(self._cache) > 500:
            now = time.time()
            expired = [k for k, (ts, _) in self._cache.items() if now - ts > self._cache_ttl]
            for k in expired:
                del self._cache[k]
        self._cache[key] = (time.time(), data)

    async def _enforce_rate_limit(self):
        async with self._rate_limit_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                sleep_needed = self._min_interval - elapsed
                await asyncio.sleep(sleep_needed)
            self._last_request_time = time.time()

    async def generate_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Generates structured JSON from Gemini with automatic rate-limiting,
        in-memory TTL caching, and exponential backoff on transient errors.
        """
        if not self.is_available:
            return None

        cache_key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result

        from google.genai import types

        max_retries = 3
        backoff = 2.0

        candidate_models = [
            self.model,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash",
        ]
        # Deduplicate preserving order
        models_to_try = []
        for m in candidate_models:
            if m and m not in models_to_try:
                models_to_try.append(m)

        for current_model in models_to_try:
            for attempt in range(max_retries):
                try:
                    await self._enforce_rate_limit()

                    # Run synchronous SDK call in thread pool to avoid blocking async event loop
                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda m=current_model: self._client.models.generate_content(
                            model=m,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.2,
                            )
                        )
                    )

                    if response and response.text:
                        parsed = json.loads(response.text)
                        self.model = current_model
                        self._set_cache(cache_key, parsed)
                        return parsed
                    break

                except Exception as e:
                    err_str = str(e).lower()
                    if "404" in err_str or "no longer available" in err_str or "not_found" in err_str:
                        logger.warning(
                            f"Model {current_model} not available ({e}). Falling back to next candidate."
                        )
                        break

                    is_rate_limited = "429" in err_str or "resource_exhausted" in err_str
                    if is_rate_limited and attempt < max_retries - 1:
                        logger.warning(
                            f"Gemini rate limit hit on attempt {attempt + 1}. Backing off for {backoff} seconds."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                    else:
                        logger.error(f"Gemini API request failed on attempt {attempt + 1}: {e}")
                        if attempt == max_retries - 1:
                            break
                        await asyncio.sleep(1.0)

        return None

    async def batch_categorize_transactions(
        self,
        descriptions: List[str],
        categories: List[str]
    ) -> List[Dict[str, str]]:
        """
        Tier 3 LLM fallback: classifies a batch of ambiguous transaction descriptions
        into one of the standard categories.
        """
        if not self.is_available or not descriptions:
            return []

        categories_str = ", ".join(f'"{c}"' for c in categories)
        txns_formatted = "\n".join(f"{idx + 1}. \"{desc}\"" for idx, desc in enumerate(descriptions))

        prompt = f"""You are an expert financial transaction categorizer specializing in Indian bank statements.
Classify each numbered transaction description into exactly one category from this allowed list:
[{categories_str}]

Transactions to classify:
{txns_formatted}

Respond in valid JSON format as a list of objects with "index" (integer) and "category" (string from allowed list):
[
  {{"index": 1, "category": "Food & Dining"}}
]
"""
        result = await self.generate_json(prompt)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "classifications" in result:
            return result["classifications"]
        return []

gemini_client = GeminiClient()
