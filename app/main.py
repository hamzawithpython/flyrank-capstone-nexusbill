from fastapi import FastAPI
from app.api.routes import auth, organizations, projects, keys, usage, billing
from app.api.v1 import completions as v1

app = FastAPI(title="NexusBill")
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(projects.router)
app.include_router(keys.router)
app.include_router(usage.router)
app.include_router(billing.router)
app.include_router(v1.router)

@app.get("/health")
def health():
    return {"status": "ok"}