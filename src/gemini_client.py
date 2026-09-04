import json
from google import genai
from google.genai import types
from pydantic import BaseModel
from src.config import config

class GeminiClient:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            
    def get_structured_completion(self, prompt: str, schema_class: type[BaseModel] = None, model: str = "gemini-3.5-flash-lite") -> str:
        if not self.client:
            raise Exception("GEMINI_API_KEY not configured")
        
        try:
            config_dict = {
                "temperature": 0.0, # Deterministic behavior
                "response_mime_type": "application/json"
            }
            if schema_class:
                config_dict["response_schema"] = schema_class
                
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_dict)
            )
            return response.text
        except Exception as e:
            # Fallback for API errors
            print(f"Gemini API Error: {e}")
            raise

gemini_client = GeminiClient()
