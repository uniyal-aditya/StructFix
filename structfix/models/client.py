"""Ollama HTTP Client for Tier 2 Semantic Repair."""

from __future__ import annotations

import os
from typing import Any
import requests

from structfix.repair.parser import strip_thinking_tags


class OllamaClient:
    """Client for interacting with local Ollama API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("OLLAMA_HOST")
            or os.environ.get("OLLAMA_URL")
            or "http://localhost:11434"
        ).rstrip("/")
        self.timeout = timeout

    def check_health(self) -> dict[str, Any]:
        """Check connection to Ollama and list available models."""
        endpoint = f"{self.base_url}/api/tags"
        headers = {
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "StructFix/0.1.0",
        }
        try:
            res = requests.get(endpoint, headers=headers, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "reachable": True,
                    "base_url": self.base_url,
                    "models": models,
                }
            return {
                "reachable": False,
                "base_url": self.base_url,
                "error": f"HTTP {res.status_code}",
                "models": [],
            }
        except Exception as e:
            return {
                "reachable": False,
                "base_url": self.base_url,
                "error": str(e),
                "models": [],
            }

    def generate(
        self,
        prompt: str,
        model: str = "qwen3:1.7b",
        schema: dict[str, Any] | None = None,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """Call Ollama /api/generate with JSON schema format and disabled thinking.

        Args:
            prompt: User repair prompt with malformed output and schema errors.
            model: Target model name (e.g. "qwen3:1.7b", "llama3.2").
            schema: Optional JSON Schema passed to Ollama's `format` parameter.
            system: Optional system prompt instructions.
            temperature: Sampling temperature (default 0.0 for deterministic repair).

        Returns:
            The raw text response from the model with thinking blocks stripped.
        """
        endpoint = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "think": False,
            },
        }

        if system:
            payload["system"] = system

        if schema:
            payload["format"] = schema

        headers = {
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "StructFix/0.1.0",
        }
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            res_data = response.json()
            raw_response = res_data.get("response", "")
            return strip_thinking_tags(raw_response)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running (`ollama serve`)."
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(
                f"Ollama request timed out after {self.timeout}s at {endpoint}."
            ) from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e
