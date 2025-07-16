import os

from fastapi import FastAPI
from app.routes import auth, audio, dataset_route
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.auth import models  # обязательно, чтобы модель подгрузилась

# создаёт таблицы, если их нет
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TTS Audio Validator")

# 🔓 Настройка CORS — разрешить всё
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(audio.router)
app.include_router(dataset_route.router)


app.mount("/audio", StaticFiles(directory=os.path.abspath("../../")), name="audio")

@app.get("/")
def read_root():
    return {"message": "Приложение работает!"}
