from fastapi import FastAPI
from app.api.routes import auth

app = FastAPI(title="NexusBill")
app.include_router(auth.router)

@app.get("/health")
def health():
    return {"status": "ok"}