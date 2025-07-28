from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.services.audio_service import (
    get_audio_filenames_by_dataset_id,
    get_audio_file_by_dataset_id_and_name
)
from fastapi.responses import FileResponse

router = APIRouter(prefix="/audio", tags=["audio"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Настройка схемы авторизации
def get_current_user(request: Request):
    return {
        "sub": "admin",
        "role": "admin"
    }
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated: access_token cookie missing")
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload

@router.get("/get")
def get_audio_file(
    audio_path: str = Query(..., description="Relative audio path, e.g. uzak_jol_wavs/uzak_jol_10_b_005.wav"),
    user=Depends(get_current_user)  # 👈 добавляем авторизацию
):
    # Строим путь относительно datasets.json (выше на 3 папки от этого файла)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    abs_file_path = os.path.abspath(os.path.join(base_dir, audio_path))

    # Проверяем, что путь не вышел за пределы base_dir (защита от ../../ атак)
    if not abs_file_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Invalid file path")

    # Проверяем, что файл существует
    if not os.path.isfile(abs_file_path):
        raise HTTPException(status_code=404, detail=f"Audio file: {abs_file_path} not found")

    # Отдаём файл
    return FileResponse(abs_file_path, media_type="audio/wav")


@router.get("/list")
def list_audio_segments(
    dataset_id: int = Query(..., description="ID датасета"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    files, total = get_audio_filenames_by_dataset_id(dataset_id, db, page, limit)
    return {
        "dataset_id": dataset_id,
        "page": page,
        "limit": limit,
        "total": total,
        "files": files
    }

@router.get("/stream")
def stream_audio_segment(
    dataset_id: int = Query(..., description="ID датасета"),
    filename: str = Query(..., description="Имя сегмента (например: segment_001.wav)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return get_audio_file_by_dataset_id_and_name(dataset_id, filename, db)

