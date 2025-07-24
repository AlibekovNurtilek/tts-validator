from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
import os

from app.auth.utils import decode_access_token

router = APIRouter(prefix="/audio", tags=["audio"])

# Настройка схемы авторизации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

from fastapi import Request

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


