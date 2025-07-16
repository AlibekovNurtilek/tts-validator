from math import ceil
from fastapi import APIRouter, HTTPException, Query, Body, Depends
import os
import json
import wave

from app.auth.utils import decode_access_token
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

router = APIRouter(prefix="/datasets", tags=["dataset"])

DATASETS_FILE = os.path.join(os.path.dirname(__file__), "../../datasets.json")

def format_duration(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@router.get("/info")
def get_datasets_info(user=Depends(get_current_user)):
    if not os.path.exists(DATASETS_FILE):
        return []

    with open(DATASETS_FILE, "r", encoding="utf-8") as f:
        datasets = json.load(f)

    result = []
    for ds in datasets:
        txt_path = os.path.join(os.path.dirname(DATASETS_FILE), ds["txt_path"])
        sample_count = 0

        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as txt_file:
                sample_count = sum(1 for _ in txt_file)

        total_seconds = ds.get("total_duration_seconds", 0)
        total_duration = format_duration(total_seconds)

        result.append({
            "id": ds["id"],
            "name": ds["name"],
            "sample_count": sample_count,
            "total_duration": total_duration
        })

    return result





@router.get("/{dataset_id}/records")
def get_records(
    dataset_id: int,
    page: int = 1,
    limit: int = 10,
    q: str = Query("", alias="q"),
    user=Depends(get_current_user)  # 👈 добавляем зависимость авторизации
):
    if not os.path.exists(DATASETS_FILE):
        raise HTTPException(status_code=500, detail="datasets.json not found")

    with open(DATASETS_FILE, "r", encoding="utf-8") as f:
        datasets = json.load(f)

    dataset = next((ds for ds in datasets if ds["id"] == dataset_id), None)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    txt_path = os.path.join(os.path.dirname(DATASETS_FILE), dataset["txt_path"])
    wav_path = dataset["wav_path"].strip("/")

    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail=f"TXT file: {txt_path} not found")

    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if q.strip():
        filtered = [line for line in lines if q.lower() in line.split("|")[1].lower()]
    else:
        filtered = lines

    total = len(filtered)
    total_pages = ceil(total / limit)
    start = (page - 1) * limit
    end = start + limit

    if start >= total:
        return {"page": page, "total": total, "total_pages": total_pages, "records": []}

    selected_lines = filtered[start:end]
    records = []

    for line in selected_lines:
        parts = line.strip().split("|")
        if len(parts) != 2:
            continue
        file_name, text = parts

        # Формируем путь как uzak_jol_wavs/uzak_jol_10_b_001.wav
        audio_path = f"{wav_path}/{file_name}.wav"

        records.append({
            "index": file_name,
            "text": text,
            "audio_url": audio_path  # меняем название на audio_path
        })

    return {
        "page": page,
        "total": total,
        "total_pages": total_pages,
        "records": records
    }


@router.put("/{dataset_id}/records/{filename}")
def update_record_text(dataset_id: int, filename: str, new_text: str = Body(..., embed=True), user=Depends(get_current_user)):
    if not os.path.exists(DATASETS_FILE):
        raise HTTPException(status_code=500, detail="datasets.json not found")

    with open(DATASETS_FILE, "r", encoding="utf-8") as f:
        datasets = json.load(f)

    dataset = next((ds for ds in datasets if ds["id"] == dataset_id), None)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    txt_path = os.path.join(os.path.dirname(DATASETS_FILE), dataset["txt_path"])

    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="TXT file not found")

    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        parts = line.strip().split("|")
        if len(parts) != 2:
            continue
        file_name = parts[0]
        if file_name == filename:
            lines[i] = f"{file_name}|{new_text.strip()}\n"
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Filename not found")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return {"message": "Record updated successfully"}

def get_wav_duration_seconds(file_path: str) -> float:
    try:
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except Exception as e:
        print(f"Error reading WAV file: {file_path} - {e}")
        return 0.0

@router.delete("/dataset/{dataset_id}/records/{filename}")
def delete_record(dataset_id: int, filename: str, user=Depends(get_current_user)):
    if not os.path.exists(DATASETS_FILE):
        raise HTTPException(status_code=500, detail="datasets.json not found")

    with open(DATASETS_FILE, "r", encoding="utf-8") as f:
        datasets = json.load(f)

    dataset = next((ds for ds in datasets if ds["id"] == dataset_id), None)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    txt_path = os.path.join(os.path.dirname(DATASETS_FILE), dataset["txt_path"])
    wav_dir = os.path.join(os.path.dirname(DATASETS_FILE), "../" + dataset["wav_path"])

    if not os.path.exists(txt_path):
        raise HTTPException(status_code=404, detail="TXT file not found")

    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    line_index = next((i for i, line in enumerate(lines) if line.split("|")[0] == filename), None)
    if line_index is None:
        raise HTTPException(status_code=404, detail="Filename not found")

    wav_path = os.path.join(wav_dir, f"{filename}.wav")
    duration_to_subtract = get_wav_duration_seconds(wav_path)

    del lines[line_index]

    with open(txt_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    for ds in datasets:
        if ds["id"] == dataset_id:
            old_total = ds.get("total_duration_seconds", 0)
            ds["total_duration_seconds"] = max(0, old_total - duration_to_subtract)
            break

    with open(DATASETS_FILE, "w", encoding="utf-8") as f:
        json.dump(datasets, f, ensure_ascii=False, indent=2)

    return {
        "message": "Record deleted successfully",
        "removed_duration_seconds": duration_to_subtract,
        "new_total_duration_seconds": ds["total_duration_seconds"]
    }
