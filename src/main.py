from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from providers import ProviderError, ask_nvidia
from router import ModelRouter, TaskType

app = FastAPI(title="Sakura.IA Cloud", version="0.2.0")
router = ModelRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    task: TaskType = TaskType.CHAT
    private_only: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "service": "sakura-ia", "version": app.version}


@app.get("/models")
def models():
    return {"providers": router.catalog()}


@app.post("/plan")
def plan(request: ChatRequest):
    result = router.plan(request.task, request.private_only)
    if result["status"] != "ready":
        raise HTTPException(status_code=503, detail=result)
    return result


@app.post("/chat")
async def chat(request: ChatRequest):
    """Send a chat request through the first configured real provider."""
    if request.private_only:
        return {
            "status": "local_provider_pending",
            "message": "O modo privado exige um modelo local configurado.",
        }
    try:
        result = await ask_nvidia([{"role": "user", "content": request.message}])
        return {"status": "ok", "router": router.plan(request.task), **result}
    except ProviderError as exc:
        return {
            "status": "provider_unavailable",
            "router": router.plan(request.task),
            "error": str(exc),
            "next_step": "fallback_provider",
        }
