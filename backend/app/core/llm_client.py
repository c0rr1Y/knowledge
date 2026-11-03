"""LLM client for Anthropic-compatible API with streaming support."""

import httpx
import json
from typing import AsyncGenerator, Optional
from app.config import settings


class LLMClient:
    """Anthropic Messages API client (streaming + non-streaming)."""

    def __init__(self):
        self.base_url = settings.anthropic_base_url.rstrip("/")
        self.token = settings.anthropic_auth_token
        self.model = settings.anthropic_model

    def _get_headers(self) -> dict:
        return {
            "x-api-key": self.token,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream chat via Anthropic Messages API.

        Handles extended thinking blocks — only yields text content.
        On any streaming failure, falls back to non-streaming so the user always gets an answer.
        """
        try:
            async for chunk in self._stream_anthropic(messages):
                yield chunk
            return
        except Exception as e:
            print(f"[LLM] Stream error: {e}, falling back to non-streaming")

        # Fallback: non-streaming
        try:
            full = await self.chat(messages)
            if full:
                yield full
        except Exception as e:
            print(f"[LLM] Non-stream fallback also failed: {e}")
            yield "抱歉，AI 服务暂时不可用，请稍后重试。"

    async def _stream_anthropic(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Anthropic SSE streaming with thinking-block awareness."""
        system_prompt = ""
        api_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": api_messages,
            "stream": True,
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json=body,
            ) as response:
                response.raise_for_status()

                current_block_type = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    evt_type = event.get("type", "")

                    # Track which content block we're in (thinking vs text)
                    if evt_type == "content_block_start":
                        block = event.get("content_block", {})
                        current_block_type = block.get("type", "")

                    elif evt_type == "content_block_delta":
                        delta = event.get("delta", {})
                        # Only yield text, skip thinking blocks
                        if current_block_type == "text":
                            text = delta.get("text", "")
                            if text:
                                yield text

                    elif evt_type == "message_delta":
                        pass  # usage stats, ignore

                    elif evt_type == "message_stop":
                        break

    async def chat(self, messages: list[dict]) -> str:
        """Non-streaming fallback using Anthropic Messages API."""
        system_prompt = ""
        api_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": api_messages,
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            # The API returns content blocks — find the text one
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block.get("text", "")
            return ""


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
