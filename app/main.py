import os
from fastapi import FastAPI
from app.routes import audio_route, auth_route, dataset_route, speaker_route, sample_route, transcription_router
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.db import Base, engine
from app.auth import models  # обязательно, чтобы модель подгрузилась
from app.models import datasets, samples, speakers

# создаёт таблицы, если их нет
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TTS Audio Validator2 ")

# 🔓 Настройка CORS — разрешить всё
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8082",
        "http://80.72.180.130:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_route.router)
app.include_router(audio_route.router)
app.include_router(dataset_route.router)
app.include_router(speaker_route.router)
app.include_router(sample_route.router)
app.include_router(transcription_router.router)


#app.mount("/audio", StaticFiles(directory=os.path.abspath("../../")), name="audio")

@app.get("/")
def read_root():
    return {"Apllication running"}
