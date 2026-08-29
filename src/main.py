from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from router import ModelRouter, TaskType

app = FastAPI(title="Sakura.IA Cloud", version="0.1.0")
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
def chat(request: ChatRequest):
    """V1 intentionally returns a transparent execution plan.

    Provider adapters are the next layer. No prompt is sent anywhere until an
    adapter is explicitly configured, keeping this first version safe.
    """
    result = router.plan(request.task, request.private_only)
    return {
        "message": request.message,
        "router": result,
        "next_step": "provider_adapter_not_configured",
    }
