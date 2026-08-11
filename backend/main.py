from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.embedding_service import close_voyage_client

from app.api.routes import auth, profile
from app.core.config import settings
from app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)


@app.get("/")
def root():
    return {"message": f"{settings.app_name} API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.on_event("shutdown")
async def shutdown_event():
    await close_voyage_client()
