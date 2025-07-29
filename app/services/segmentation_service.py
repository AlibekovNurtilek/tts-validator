import os
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import librosa
import scipy.signal
from pydub import AudioSegment

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def segment_audio(
    input_wav_path: str,
    output_dir: str,
    min_length: float = 1.5,
    max_length: float = 12.0,
) -> Dict:
    """
    Сегментирует аудиофайл по тишине по алгоритму Qwen.
    
    Аргументы:
        input_wav_path (str): Путь к входному .wav файлу.
        output_dir (str): Директория для сохранения сегментов.
        min_length (float): Минимальная длина сегмента (в секундах).
        max_length (float): Максимальная длина сегмента (в секундах).
    
    Возвращает:
        Dict: Результат в формате {
            'status': 'success' или 'error',
            'message': сообщение,
            'segments_count': int,
            'stats': {
                'min_duration': float,
                'max_duration': float,
                'avg_duration': float,
                'total_segments': int
            }
        }
    """
    input_path = Path(input_wav_path)
    output_path = Path(output_dir)

    # Проверки
    if not input_path.exists():
        return {
            'status': 'error',
            'message': f"Файл не найден: {input_wav_path}",
            'segments_count': 0,
            'stats': {}
        }

    if input_path.suffix.lower() != '.wav':
        return {
            'status': 'error',
            'message': "Поддерживаются только .wav файлы",
            'segments_count': 0,
            'stats': {}
        }

    try:
        # Создаём директорию для сегментов
        if output_path.exists():
            shutil.rmtree(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Загружаем аудио
        audio_np, sr = librosa.load(input_path, sr=None, mono=True)
        logger.info(f"Аудио загружено: {input_wav_path}, sample rate: {sr} Hz")

        # Нормализуем аудио
        if np.max(np.abs(audio_np)) > 0:
            audio_np = audio_np / np.max(np.abs(audio_np))

        # Сегментация
        chunks = _qwen_split_at_silence(
            audio_np, sr, min_length=min_length, max_length=max_length
        )

        if not chunks:
            return {
                'status': 'error',
                'message': 'Сегменты не были созданы.',
                'segments_count': 0,
                'stats': {}
            }

        # Экспорт сегментов
        durations = []
        for i, chunk in enumerate(chunks, 1):
            duration_sec = len(chunk) / sr
            durations.append(duration_sec)

            # Конвертируем в int16
            chunk_int16 = (chunk * 32767).astype(np.int16)

            # Создаём AudioSegment
            audio_segment = AudioSegment(
                chunk_int16.tobytes(),
                frame_rate=sr,
                sample_width=2,
                channels=1
            )

            # Сохраняем
            filename = f"segment_{i:04d}.wav"
            filepath = output_path / filename
            audio_segment.export(str(filepath), format="wav")

        # Статистика
        stats = {
            'min_duration': round(min(durations), 2),
            'max_duration': round(max(durations), 2),
            'avg_duration': round(sum(durations) / len(durations), 2),
            'total_segments': len(durations)
        }

        logger.info(f"Сегментация завершена: {len(durations)} сегментов.")
        return {
            'status': 'success',
            'message': 'Сегментация успешно выполнена.',
            'segments_count': len(durations),
            'stats': stats
        }

    except Exception as e:
        logger.error(f"Ошибка при сегментации: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f"Внутренняя ошибка: {str(e)}",
            'segments_count': 0,
            'stats': {}
        }


# --- Внутренние функции (алгоритм Qwen) ---

def _qwen_split_at_silence(
    audio: np.ndarray,
    sr: int,
    min_length: float = 1.5,
    max_length: float = 12.0
) -> List[np.ndarray]:
    """
    Алгоритм разбиения по тишине, как в оригинальном скрипте.
    """
    target_samples = int(max_length * sr)
    min_silence_samples = int(0.3 * sr)
    min_chunk_samples = int(min_length * sr)
    total_samples = len(audio)

    chunks = []
    start = 0

    while start < total_samples:
        ideal_end = min(start + target_samples, total_samples)

        # Если остался хвост — добавляем как последний сегмент
        if ideal_end >= total_samples - sr:
            if total_samples - start > 0:
                chunks.append(audio[start:total_samples])
            break

        # Определяем окно поиска
        search_window_size = min(int(8 * sr), total_samples - ideal_end)
        search_start = max(ideal_end - search_window_size // 2, start)
        search_end = min(search_start + search_window_size, total_samples)
        search_end = min(search_end, ideal_end + int(4 * sr))

        # Ищем точку разбиения
        split_point = _qwen_find_silence_point(
            audio, sr, search_start, search_end, min_silence_samples, silence_threshold=0.01
        )

        # Принудительный минимум длины сегмента
        if split_point - start < min_chunk_samples:
            split_point = min(start + target_samples, total_samples)

        if split_point > start:
            chunks.append(audio[start:split_point])
        start = split_point

        if start >= total_samples - 1:
            break

    return chunks


def _qwen_find_silence_point(
    audio: np.ndarray,
    sr: int,
    segment_start: int,
    segment_end: int,
    min_silence_samples: int,
    silence_threshold: float
) -> int:
    segment = audio[segment_start:segment_end]
    segment_length = len(segment)

    if segment_length <= min_silence_samples:
        return segment_start + segment_length // 2

    window_size = max(int(0.02 * sr), 100)
    hop_size = window_size // 4
    energies = []

    for i in range(0, segment_length - window_size, hop_size):
        window = segment[i:i + window_size]
        energy = np.sqrt(np.mean(window ** 2))
        center_pos = segment_start + i + window_size // 2
        energies.append((center_pos, energy))

    if not energies:
        return segment_start + segment_length // 2

    # Ищем тихие участки
    silence_points = [(pos, energy) for pos, energy in energies if energy < silence_threshold]

    if not silence_points:
        return _qwen_find_optimal_split_point(energies, segment_start, segment_end)

    # Группируем тишину
    silence_regions = _qwen_group_silence_regions(silence_points, min_silence_samples)

    if not silence_regions:
        return _qwen_find_optimal_split_point(energies, segment_start, segment_end)

    # Выбираем лучшую точку
    return _qwen_select_best_silence_region(silence_regions, segment_start, segment_end, sr)


def _qwen_group_silence_regions(silence_points, min_duration_samples):
    if not silence_points:
        return []
    regions = []
    current_region = [silence_points[0]]
    for i in range(1, len(silence_points)):
        prev_pos, _ = silence_points[i-1]
        curr_pos, _ = silence_points[i]
        if curr_pos - prev_pos <= min_duration_samples // 2:
            current_region.append(silence_points[i])
        else:
            if len(current_region) >= min_duration_samples // 10:
                regions.append(current_region)
            current_region = [silence_points[i]]
    if len(current_region) >= min_duration_samples // 10:
        regions.append(current_region)
    return regions


def _qwen_select_best_silence_region(regions, segment_start, segment_end, sr):
    segment_center = (segment_start + segment_end) // 2
    best_score = -1
    best_position = segment_center
    for region in regions:
        region_start = region[0][0]
        region_end = region[-1][0]
        region_duration = region_end - region_start
        region_center = (region_start + region_end) // 2
        centrality = 1.0 - abs(region_center - segment_center) / (segment_end - segment_start) * 2
        duration_score = min(region_duration / sr, 1.0)
        score = duration_score * 0.7 + centrality * 0.3
        if score > best_score:
            best_score = score
            best_position = region_center
    return best_position


def _qwen_find_optimal_split_point(energies, segment_start, segment_end):
    if not energies:
        return (segment_start + segment_end) // 2
    energy_values = [e[1] for e in energies]
    positions = [e[0] for e in energies]
    if len(energy_values) < 3:
        return positions[len(positions) // 2]
    local_minima_indices = scipy.signal.argrelextrema(np.array(energy_values), np.less)[0]
    if local_minima_indices.size > 0:
        min_energy = float('inf')
        best_pos = -1
        for idx in local_minima_indices:
            if energy_values[idx] < min_energy:
                min_energy = energy_values[idx]
                best_pos = positions[idx]
        return best_pos
    else:
        return positions[np.argmin(energy_values)]

