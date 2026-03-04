from __future__ import annotations

import json
from abc import ABC, abstractmethod
from urllib import request
from urllib.error import HTTPError, URLError

from .config import Settings


class ProviderError(RuntimeError):
    """Errors raised by model providers."""


class ChatProvider(ABC):
    @abstractmethod
    def chat(self, question: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise ProviderError(f"网络错误: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError("响应不是合法 JSON。") from exc


class OpenAIProvider(ChatProvider):
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY 未设置。")
        self.model = settings.model
        self.base_url = settings.openai_base_url
        self.api_key = settings.openai_api_key
        self.timeout = settings.timeout

    def chat(self, question: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})

        data = _post_json(
            url=f"{self.base_url}/chat/completions",
            payload={"model": self.model, "messages": messages},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"OpenAI 返回格式异常: {data}") from exc


class AnthropicProvider(ChatProvider):
    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY 未设置。")
        self.model = settings.model
        self.base_url = settings.anthropic_base_url
        self.api_key = settings.anthropic_api_key
        self.timeout = settings.timeout

    def chat(self, question: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": question}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        data = _post_json(
            url=f"{self.base_url}/v1/messages",
            payload=payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=self.timeout,
        )
        try:
            return data["content"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Anthropic 返回格式异常: {data}") from exc


class OllamaProvider(ChatProvider):
    def __init__(self, settings: Settings):
        self.model = settings.model
        self.base_url = settings.ollama_base_url
        self.timeout = settings.timeout

    def chat(self, question: str, system_prompt: str | None = None) -> str:
        prompt = question if not system_prompt else f"{system_prompt}\n\n用户问题：{question}"
        data = _post_json(
            url=f"{self.base_url}/api/generate",
            payload={"model": self.model, "prompt": prompt, "stream": False},
            headers={},
            timeout=self.timeout,
        )
        text = data.get("response")
        if not isinstance(text, str):
            raise ProviderError(f"Ollama 返回格式异常: {data}")
        return text.strip()


def build_provider(settings: Settings) -> ChatProvider:
    providers: dict[str, type[ChatProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
    }
    provider_name = settings.provider
    provider_cls = providers.get(provider_name)
    if not provider_cls:
        valid = ", ".join(providers)
        raise ProviderError(f"不支持的 AI_PROVIDER={provider_name}。可选: {valid}")
    return provider_cls(settings)
