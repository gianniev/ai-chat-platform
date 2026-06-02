from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from routers.chat import router as chat_router
from routers.conversations import router as conversations_router
from routers.health import router as health_router
from routers.analytics import router as analytics_router
from routers.legacy import router as legacy_router
from settings import CORS_ORIGINS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(legacy_router)
