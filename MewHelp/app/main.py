from fastapi import FastAPI

from app.api.chat import router as chat_router


app = FastAPI(title="MewHelp Ch01")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
