"""
Thin wrapper around the Gemini client used for narrative generation.

The wrapper never raises: on any failure it logs, increments a metric and
returns ``None`` so callers fall back to deterministic text. This keeps the
risk prediction path independent from LLM availability.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

from .config import settings
from .observability import LLM_FAILURES

logger = logging.getLogger(__name__)

_BROKEN_PROXIES = {"http://127.0.0.1:9", "https://127.0.0.1:9"}
_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


@contextmanager
def _without_broken_proxies():
    removed = {}
    for key in _PROXY_KEYS:
        if os.environ.get(key) in _BROKEN_PROXIES:
            removed[key] = os.environ.pop(key)
    try:
        yield
    finally:
        os.environ.update(removed)


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout_ms: int | None = None):
        self.api_key = (api_key if api_key is not None else settings.gemini_api_key) or ""
        self.model = model or settings.gemini_model
        self.timeout_ms = timeout_ms or settings.gemini_timeout_ms
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout_ms),
            )
        return self._client

    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 400,
    ) -> str | None:
        if not self.available:
            return None

        try:
            from google.genai import types

            with _without_broken_proxies():
                client = self._get_client()
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                )
            text = getattr(response, "text", None)
            if not text or not text.strip():
                LLM_FAILURES.labels("empty_response").inc()
                return None
            return text.strip()
        except Exception as exc:  # noqa: BLE001 - never let the LLM break predictions
            LLM_FAILURES.labels("exception").inc()
            logger.warning("Gemini request failed: %s", exc)
            return None


gemini_client = GeminiClient()
