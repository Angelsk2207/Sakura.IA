"""Provider adapters for Sakura.IA.

Secrets are read only from server environment variables.
"""
import os
from typing import Any

import httpx


class ProviderError(RuntimeError):
    pass


async def ask_nvidia(messages: list[dict[str, str]]) -> dict[str, Any]:
    api_key = os.getenv("NVIDIA_API_KEY", "")
    if not api_key:
        raise ProviderError("NVIDIA_API_KEY is not configured")

    model = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-flash-0731")
    payload = {"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 2048}
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise ProviderError(f"NVIDIA connection failed: {exc}") from exc

    if response.status_code >= 400:
        raise ProviderError(f"NVIDIA returned HTTP {response.status_code}")
    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("NVIDIA returned an unexpected response") from exc
    return {"provider": "nvidia_nim", "model": model, "text": text}


async def ask_cloudflare(messages: list[dict[str, str]]) -> dict[str, Any]:
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    if not api_token or not account_id:
        raise ProviderError("Cloudflare credentials are not configured")

    model = os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, headers=headers, json={"messages": messages})
    except httpx.HTTPError as exc:
        raise ProviderError(f"Cloudflare connection failed: {exc}") from exc

    if response.status_code >= 400:
        raise ProviderError(f"Cloudflare returned HTTP {response.status_code}")
    data = response.json()
    result = data.get("result", data)
    text = result.get("response") if isinstance(result, dict) else None
    if not text:
        raise ProviderError("Cloudflare returned an unexpected response")
    return {"provider": "cloudflare", "model": model, "text": text}
