
import os
import time
from typing import List, Dict, Any, Optional

class ModelClient:
    """
    Abstract chat client. Implement generate(messages) -> str
    messages: list of dicts with keys: role in {"system","user","assistant"}, content: str
    """
    def __init__(self, model: str):
        self.model = model

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7) -> str:
        raise NotImplementedError

class OpenRouterClient(ModelClient):
    """
    Uses OpenRouter (OpenAI-compatible) Chat Completions API for all models.
    Requires: pip install openai
    Env: OPENROUTER_API_KEY
         optional: OPENROUTER_BASE_URL (default https://openrouter.ai/api/v1)
                   OPENROUTER_APP_URL, OPENROUTER_APP_NAME (for attribution headers)
    """
    def __init__(self, model: str):
        super().__init__(model)
        try:
            import openai  # type: ignore
        except Exception as e:
            raise RuntimeError("Please pip install openai to use OpenRouterClient") from e
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        default_headers = {}
        app_url = os.getenv("OPENROUTER_APP_URL")
        app_name = os.getenv("OPENROUTER_APP_NAME")
        if app_url:
            default_headers["HTTP-Referer"] = app_url
        if app_name:
            default_headers["X-Title"] = app_name
        # Some versions of the SDK prefer None if no headers are provided
        default_headers = default_headers or None
        self._client = openai.OpenAI(api_key=key, base_url=base_url, default_headers=default_headers)

    def generate(self, messages, max_tokens: int = 512, temperature: float = 0.7) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

class OpenAIChatClient(ModelClient):
    """
    Uses OpenAI compatible API. Also works with vLLM or other OpenAI-compatible endpoints by setting OPENAI_BASE_URL.
    Requires: pip install openai
    Env: OPENAI_API_KEY, optional OPENAI_BASE_URL
    """
    def __init__(self, model: str):
        super().__init__(model)
        try:
            import openai  # type: ignore
        except Exception as e:
            raise RuntimeError("Please pip install openai to use OpenAIChatClient") from e
        self._openai = openai
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            self._openai.base_url = base_url
        self._client = self._openai.OpenAI(api_key=key, base_url=base_url) if hasattr(self._openai, "OpenAI") else None
        # Back compat: fall back to old openai.ChatCompletion if needed

    def generate(self, messages, max_tokens: int = 512, temperature: float = 0.7) -> str:
        # Try new client first
        if self._client is not None:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        # Old API fallback
        completion = self._openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion["choices"][0]["message"]["content"]

class AnthropicClient(ModelClient):
    """
    Uses Anthropic Messages API.
    Requires: pip install anthropic
    Env: ANTHROPIC_API_KEY
    """
    def __init__(self, model: str):
        super().__init__(model)
        try:
            import anthropic  # type: ignore
        except Exception as e:
            raise RuntimeError("Please pip install anthropic to use AnthropicClient") from e
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=key)

    def generate(self, messages, max_tokens: int = 512, temperature: float = 0.7) -> str:
        # Convert OpenAI-style to Anthropic messages
        system = ""
        user_parts = []
        for m in messages:
            if m["role"] == "system":
                system += m["content"] + "\n"
            elif m["role"] == "user":
                user_parts.append({"type": "text", "text": m["content"]})
            elif m["role"] == "assistant":
                user_parts.append({"type": "text", "text": "[assistant prior] " + m["content"]})
        resp = self._client.messages.create(
            model=self.model,
            system=system or None,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user_parts}],
        )
        # Join text blocks
        out = []
        for blk in resp.content:
            if getattr(blk, "type", None) == "text":
                out.append(blk.text)
            elif isinstance(blk, dict) and blk.get("type") == "text":
                out.append(blk.get("text",""))
        return "\n".join(out)

class OllamaClient(ModelClient):
    """
    Local Ollama chat.
    Requires: pip install requests
    Env: OLLAMA_BASE_URL (default http://localhost:11434)
    """
    def __init__(self, model: str):
        super().__init__(model)
        try:
            import requests  # noqa: F401
        except Exception as e:
            raise RuntimeError("Please pip install requests to use OllamaClient") from e
        self.base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def generate(self, messages, max_tokens: int = 512, temperature: float = 0.7) -> str:
        import requests
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        r = requests.post(self.base + "/api/chat", json=payload, timeout=600)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")
