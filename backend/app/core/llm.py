"""LLM client. Wraps QwenPaw / LiteLLM with OpenAI-compatible interface.

Falls back across endpoints on error.
"""
from typing import Optional

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()


class LLMClient:
    def __init__(self):
        self.clients: list[tuple[str, AsyncOpenAI, str]] = []
        # Primary: Agnes (主人指定的主模型)
        if settings.agnes_api_key:
            self.clients.append(
                (
                    "agnes",
                    AsyncOpenAI(
                        api_key=settings.agnes_api_key,
                        base_url=settings.agnes_base_url,
                    ),
                    settings.agnes_model,
                )
            )
        if settings.qwenpaw_base_url:
            self.clients.append(
                (
                    "qwenpaw",
                    AsyncOpenAI(
                        api_key=settings.qwenpaw_api_key or "no-key",
                        base_url=settings.qwenpaw_base_url,
                    ),
                    settings.default_model,
                )
            )
        if settings.litellm_base_url:
            self.clients.append(
                (
                    "litellm",
                    AsyncOpenAI(
                        api_key=settings.litellm_api_key or "no-key",
                        base_url=settings.litellm_base_url,
                    ),
                    settings.default_model,
                )
            )

    async def chat(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        """Call LLM, return text content. Tries each configured client in order."""
        if not self.clients:
            raise RuntimeError("No LLM endpoint configured")
        last_err: Optional[Exception] = None
        for name, client, default_model in self.clients:
            try:
                kwargs = {
                    "model": model or default_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                resp = await client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                if content:
                    return content
            except Exception as e:
                logger.warning(f"LLM {name} failed: {e}")
                last_err = e
                continue
        raise RuntimeError(f"All LLM endpoints failed: {last_err}")


_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
