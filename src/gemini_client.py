import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel
from src.config import config

logger = logging.getLogger(__name__)

# Default timeout for all Gemini API calls (seconds)
GEMINI_TIMEOUT_SECONDS = 25


class GeminiTimeoutError(Exception):
    """Raised when a Gemini API call exceeds the timeout."""
    pass


class GeminiClient:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY not configured — AI features will be unavailable.")

    def get_structured_completion(
        self,
        prompt: str,
        schema_class: type[BaseModel] = None,
        model: str = "gemini-2.0-flash-lite",
        timeout: int = GEMINI_TIMEOUT_SECONDS
    ) -> str:
        if not self.client:
            raise Exception("GEMINI_API_KEY not configured")

        try:
            config_dict = {
                "temperature": 0.0,  # Deterministic behavior
                "response_mime_type": "application/json"
            }
            # We intentionally do not pass response_schema here because
            # newer Pydantic versions emit 'null' types in anyOf which
            # crashes the google.genai SDK parser.
            # The prompt already enforces the JSON structure.

            logger.debug("Calling Gemini model=%s timeout=%ds", model, timeout)

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_dict)
            )
            return response.text

        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "deadline" in err_str or "timed out" in err_str:
                logger.error("Gemini API timed out after %ds: %s", timeout, e)
                raise GeminiTimeoutError(f"Gemini API timed out after {timeout}s") from e
            logger.error("Gemini API error: %s", type(e).__name__)
            raise


gemini_client = GeminiClient()
