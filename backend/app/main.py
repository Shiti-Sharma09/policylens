from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.services.vectorstore import ensure_collection, get_qdrant_client
from app.routers import auth, upload, ask, compare, damage, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_qdrant_client()
    ensure_collection()
    yield


app = FastAPI(title="PolicyLens API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(ask.router)
app.include_router(compare.router)
app.include_router(damage.router)
app.include_router(agent.router)


@app.get("/health")
def health():
    return {"status": "ok"}
