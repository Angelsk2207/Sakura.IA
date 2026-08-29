"""Sakura model router V1.

Provider-agnostic model selection and fallback. Network adapters are intentionally
small and are added separately; this module can already rank providers, enforce
availability and produce a transparent execution plan.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    CHAT = "chat"
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    PRIVATE = "private"


@dataclass
class Provider:
    name: str
    models: list[str]
    task_types: set[TaskType]
    priority: int = 100
    available: bool = True
    remaining_credits: int | None = None
    local: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_run(self, task: TaskType, private_only: bool = False) -> bool:
        if not self.available or task not in self.task_types:
            return False
        if private_only and not self.local:
            return False
        if self.remaining_credits is not None and self.remaining_credits <= 0:
            return False
        return True


class ModelRouter:
    """Selects the best available provider and exposes transparent fallbacks."""

    def __init__(self, providers: list[Provider] | None = None):
        self.providers = providers or self.default_providers()

    @staticmethod
    def default_providers() -> list[Provider]:
        return [
            Provider("local", ["gguf", "ollama"], set(TaskType), priority=10, local=True),
            Provider("nvidia_nim", ["qwen", "llama", "mistral"], {TaskType.CHAT, TaskType.CODE}, priority=20),
            Provider("cloudflare", ["open-models"], {TaskType.CHAT, TaskType.CREATIVE}, priority=30),
            Provider("gemini", ["gemini"], set(TaskType), priority=40),
        ]

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "provider": p.name,
                "models": p.models,
                "tasks": sorted(t.value for t in p.task_types),
                "available": p.available,
                "local": p.local,
                "credits": p.remaining_credits,
                "priority": p.priority,
            }
            for p in sorted(self.providers, key=lambda item: item.priority)
        ]

    def plan(self, task: TaskType = TaskType.CHAT, private_only: bool = False) -> dict[str, Any]:
        candidates = [p for p in self.providers if p.can_run(task, private_only)]
        candidates.sort(key=lambda p: (p.priority, p.remaining_credits == 0))
        selected = candidates[0] if candidates else None
        return {
            "task": task.value,
            "private_only": private_only,
            "selected": selected.name if selected else None,
            "fallbacks": [p.name for p in candidates[1:]],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready" if selected else "no_provider_available",
        }

    def set_status(self, provider_name: str, available: bool, credits: int | None = None) -> bool:
        for provider in self.providers:
            if provider.name == provider_name:
                provider.available = available
                if credits is not None:
                    provider.remaining_credits = credits
                return True
        return False
