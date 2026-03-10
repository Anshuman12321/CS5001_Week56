"""
LLM interface for making API calls to Ollama.
Handles request/response and error handling.
"""
import requests
from dataclasses import dataclass


@dataclass
class LLMClient:
    """Client for interacting with Ollama API."""
    model_name: str = "devstral-small-2:24b-cloud"
    base_url: str = "http://localhost:11434"
    temp: float = 0.0
    request_timeout: int = 120

    def call(self, prompt_text: str) -> str:
        """
        Send a prompt to the LLM and return the response.
        Raises RuntimeError if the API call fails.
        """
        endpoint = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt_text,
            "stream": False,
            "options": {"temperature": self.temp},
        }

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                timeout=self.request_timeout
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(
                f"LLM API call failed: {e}"
            ) from e

        result = resp.json()
        response_text = result.get("response", "")
        return response_text.strip()
