from fastapi import FastAPI
from app.api.routes import auth, organizations

app = FastAPI(title="NexusBill")
app.include_router(auth.router)
app.include_router(organizations.router)

@app.get("/health")
def health():
    return {"status": "ok"}