from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.audio_dataset import AudioDataset
from app.models.speaker import Speaker
from app.schemas.dataset import DatasetCreate, DatasetUpdate, DatasetInitRequest
from app.services.speaker_service import get_or_create_speaker_by_name
import uuid
import os
from datetime import datetime
from pathlib import Path
import yt_dlp
from pydub.utils import mediainfo
import wave
from slugify import slugify 
from app.services.segmentation_service import segment_audio
from app.config import DATASET_URL



def get_all_datasets(db: Session):
    return db.query(AudioDataset).all()


def get_dataset_by_id(dataset_id: int, db: Session):
    dataset = db.query(AudioDataset).filter(AudioDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def get_datasets_by_speaker_id(speaker_id: int, db: Session):
    return db.query(AudioDataset).filter(AudioDataset.speaker_id == speaker_id).all()


def create_dataset(dataset: DatasetCreate, db: Session):
    new_dataset = AudioDataset(**dataset.dict())
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)
    return new_dataset


def update_dataset(dataset_id: int, dataset: DatasetUpdate, db: Session):
    db_dataset = db.query(AudioDataset).filter(AudioDataset.id == dataset_id).first()
    if not db_dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    for field, value in dataset.dict().items():
        setattr(db_dataset, field, value)
    db.commit()
    db.refresh(db_dataset)
    return db_dataset


def delete_dataset(dataset_id: int, db: Session):
    db_dataset = db.query(AudioDataset).filter(AudioDataset.id == dataset_id).first()
    if not db_dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(db_dataset)
    db.commit()


def initialize_dataset_service(data: DatasetInitRequest, db: Session):
    speaker = get_or_create_speaker_by_name(db, data.speaker_name)
    speaker_id = speaker.id

    # 2. Генерируем уникальное имя на основе спикера и времени
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    speaker_slug = slugify(speaker.speaker_name)
    base_name = f"{speaker_slug}_{timestamp}"
    #base_name = speaker_slug

    # 3. Пути
    datasets_root = Path(DATASET_URL)
    audio_path = datasets_root / f"{base_name}.wav"
    samples_dir = datasets_root / f"{base_name}_wavs"
    os.makedirs(samples_dir, exist_ok=True)

    # 4. Скачиваем аудио
    try:
        download_audio_from_youtube(data.url, str(audio_path.with_suffix('')))
    except Exception as e:
        raise RuntimeError(f"Ошибка при скачивании аудио: {e}")

    # 5. Обновляем путь (yt_dlp сам добавляет .wav)
    final_audio_path = audio_path

    # 6. Заглушка на семплирование
    print("[stub] Запуск семплирования аудио...")

    result = segment_audio(str(final_audio_path), str(samples_dir), 3, 15)

    if result['status'] != 'success':
        raise RuntimeError(f"Сегментация не удалась: {result['message']}")

    print(f"Создано сегментов: {result['segments_count']}")
    print(f"Статистика: {result['stats']}")

    # 7. Создаем AudioDataset только после успешной сегментации
    new_dataset = AudioDataset(
        name=base_name,
        speaker_id=speaker_id,
        url=data.url,
        full_audio_path=str(final_audio_path.resolve()),
        samples_dir=str(samples_dir.resolve()),
        count_of_samples=result['segments_count'],
        duration=get_audio_duration(str(final_audio_path)),
        created_at=datetime.utcnow(),
        last_update=datetime.utcnow()
    )
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    return {
        "message": "Инициализация завершена",
        "dataset_id": new_dataset.id,
        "audio_path": str(final_audio_path.resolve()),
        "samples_dir": str(samples_dir.resolve())
    }

def download_audio_from_youtube(url: str, output_path: str) -> str:
    """
    Скачивает .wav файл из YouTube и сохраняет по указанному пути (без расширения).
    yt_dlp сам добавляет .wav через postprocessor.
    """
    import yt_dlp

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_path + ".wav"


def get_audio_duration(audio_path: str) -> float:
    """
    Возвращает длительность .wav файла в секундах
    """
    full_path = os.path.abspath(audio_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Файл не найден: {full_path}")
    with wave.open(full_path, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)
