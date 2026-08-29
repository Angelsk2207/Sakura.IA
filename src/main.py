from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from providers import ProviderError, ask_nvidia
from router import ModelRouter, TaskType

ROOT = Path(__file__).resolve().parent.parent
WEBUI = ROOT / "webui"
app = FastAPI(title="Sakura.IA Cloud", version="0.3.0")
router = ModelRouter()
app.mount("/webui", StaticFiles(directory=WEBUI), name="webui")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    task: TaskType = TaskType.CHAT
    private_only: bool = False


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEBUI / "index.html")


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
    if request.private_only:
        return {"status": "local_provider_pending", "message": "O modo privado exige um modelo local configurado."}
    try:
        result = await ask_nvidia([{"role": "user", "content": request.message}])
        return {"status": "ok", "router": router.plan(request.task), **result}
    except ProviderError as exc:
        return {"status": "provider_unavailable", "router": router.plan(request.task), "error": str(exc), "next_step": "fallback_provider"}
