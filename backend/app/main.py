from fastapi import FastAPI
from app.routes import router
from app.database import engine
from app import models

app = FastAPI(title="ZenSpend API")
models.Base.metadata.create_all(bind=engine)

app.include_router(router)
