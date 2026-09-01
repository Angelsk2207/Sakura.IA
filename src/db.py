import os
from typing import Any

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


async def save_message(user_text: str, assistant_text: str, provider: str | None = None) -> bool:
    if not enabled():
        return False
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    payload = {"user_text": user_text, "assistant_text": assistant_text, "provider": provider}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(f"{SUPABASE_URL}/rest/v1/sakura_messages", headers=headers, json=payload)
            response.raise_for_status()
            return True
    except httpx.HTTPError:
        return False


async def recent_messages(limit: int = 30) -> list[dict[str, Any]]:
    if not enabled():
        return []
    headers = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
    params = {"select": "id,user_text,assistant_text,provider,created_at", "order": "created_at.desc", "limit": str(limit)}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(f"{SUPABASE_URL}/rest/v1/sakura_messages", headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        return []
