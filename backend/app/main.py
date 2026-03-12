import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db import Base, SessionLocal, engine
from app.routers import alarms, auth, dashboard, devices, reports, telemetry
from app.seed import seed_data

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="1.0.0")

origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_data(db)
    logger.info("服务启动完成，数据库就绪")


@app.get("/health", tags=["系统"])
def health() -> dict[str, str]:
    return {"status": "ok", "message": "服务运行正常"}


app.include_router(auth.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(alarms.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
