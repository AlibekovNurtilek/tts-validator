import os
import logging
from typing import List, Tuple

import librosa
import numpy as np
import soundfile as sf
from scipy import ndimage
from tqdm import tqdm


def segment_audio(audio_path: str, output_dir: str, min_length: float, max_length: float) -> dict:
    """
    Сегментирует аудиофайл на части с учетом пауз и заданных ограничений по длине.
    
    Args:
        audio_path (str): Путь к входному WAV файлу
        output_dir (str): Директория для сохранения сегментов
        min_length (float): Минимальная длина сегмента в секундах
        max_length (float): Максимальная длина сегмента в секундах
    
    Returns:
        dict: Статус выполнения и статистика
    """
    try:
        # Создаем выходную директорию
        os.makedirs(output_dir, exist_ok=True)
        
        # Загружаем аудио
        audio, sr = librosa.load(audio_path, sr=None)
        
        if len(audio) == 0:
            return {"status": "error", "message": "Пустой аудиофайл"}
        
        # Детектируем паузы
        silence_map = _detect_silence(audio, sr)
        pause_segments = _find_pause_segments(silence_map, sr)
        
        if len(pause_segments) == 0:
            return {"status": "error", "message": "Не найдено пауз для сегментации"}
        
        # Классифицируем паузы по качеству
        classified_pauses = _classify_pauses(pause_segments, audio, sr)
        
        # Выполняем сегментацию
        segments = _perform_segmentation(audio, sr, classified_pauses, min_length, max_length)
        
        if len(segments) == 0:
            return {"status": "error", "message": "Не удалось создать валидные сегменты"}
        
        # Сохраняем сегменты
        saved_count = _save_segments(segments, audio, sr, output_dir, audio_path)
        
        # Собираем статистику
        stats = _calculate_stats(segments, min_length, max_length, sr)
        
        return {
            "status": "success",
            "segments_count": saved_count,
            "stats": stats
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Ошибка обработки: {str(e)}"}


def _detect_silence(audio: np.ndarray, sr: int, 
                   amplitude_threshold: float = 0.01,
                   rms_threshold: float = 0.005) -> np.ndarray:
    """Детектирует тишину используя амплитуду и RMS энергию."""
    
    # Детекция по амплитуде
    amplitude_silence = np.abs(audio) < amplitude_threshold
    
    # Детекция по RMS энергии (окно 1024 сэмпла)
    hop_length = 512
    rms = librosa.feature.rms(y=audio, hop_length=hop_length, frame_length=1024)[0]
    rms_times = librosa.frames_to_samples(np.arange(len(rms)), hop_length=hop_length)
    
    # Интерполируем RMS на все сэмплы
    rms_interpolated = np.interp(np.arange(len(audio)), rms_times, rms)
    rms_silence = rms_interpolated < rms_threshold
    
    # Комбинируем оба подхода
    silence_map = amplitude_silence & rms_silence
    
    # Морфологическая обработка для очистки шума
    # Erosion для удаления коротких ложных пауз
    silence_map = ndimage.binary_erosion(silence_map, iterations=int(sr * 0.02))  # 20мс
    # Dilation для восстановления размера реальных пауз
    silence_map = ndimage.binary_dilation(silence_map, iterations=int(sr * 0.03))  # 30мс
    
    return silence_map


def _find_pause_segments(silence_map: np.ndarray, sr: int, 
                        min_pause_duration: float = 0.05) -> List[Tuple[int, int]]:
    """Находит сегменты пауз с минимальной длительностью."""
    
    min_samples = int(min_pause_duration * sr)
    
    # Находим границы пауз
    diff = np.diff(silence_map.astype(int))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1
    
    # Обрабатываем крайние случаи
    if silence_map[0]:
        starts = np.concatenate(([0], starts))
    if silence_map[-1]:
        ends = np.concatenate((ends, [len(silence_map)]))
    
    # Фильтруем по минимальной длительности
    pause_segments = []
    for start, end in zip(starts, ends):
        if end - start >= min_samples:
            pause_segments.append((start, end))
    
    return pause_segments


def _classify_pauses(pause_segments: List[Tuple[int, int]], 
                    audio: np.ndarray, sr: int) -> dict:
    """Классифицирует паузы по качеству (A, B, C класс)."""
    
    classified = {"A": [], "B": [], "C": []}
    
    for start, end in pause_segments:
        duration = (end - start) / sr
        
        # Анализируем качество паузы (уровень шума)
        pause_audio = audio[start:end]
        noise_level = np.std(pause_audio)
        
        # Классификация
        if duration >= 0.5 and noise_level < 0.003:
            classified["A"].append((start, end, duration))
        elif duration >= 0.2 and noise_level < 0.007:
            classified["B"].append((start, end, duration))
        elif duration >= 0.05 and noise_level < 0.015:
            classified["C"].append((start, end, duration))
    
    return classified


def _perform_segmentation(audio: np.ndarray, sr: int, classified_pauses: dict,
                         min_length: float, max_length: float) -> List[Tuple[int, int]]:
    """Выполняет двухпроходную сегментацию."""
    
    # Создаем отсортированный список всех пауз
    all_pauses = []
    for quality in ["A", "B", "C"]:
        for pause in classified_pauses[quality]:
            all_pauses.append((pause[0], pause[1], quality))
    
    all_pauses.sort(key=lambda x: x[0])  # Сортируем по времени начала
    
    if len(all_pauses) == 0:
        return []
    
    # Первый проход - жадная сегментация
    segments = []
    current_start = 0
    min_samples = int(min_length * sr)
    max_samples = int(max_length * sr)
    
    i = 0
    while i < len(all_pauses) and current_start < len(audio):
        best_cut = None
        search_start = current_start + min_samples
        search_end = min(current_start + max_samples, len(audio))
        
        # Ищем лучшую точку разреза в допустимом диапазоне
        for pause_start, pause_end, quality in all_pauses[i:]:
            pause_mid = (pause_start + pause_end) // 2
            
            if pause_mid < search_start:
                continue
            if pause_mid > search_end:
                break
            
            # Приоритет по качеству пауз
            priority = {"A": 3, "B": 2, "C": 1}[quality]
            
            if best_cut is None or priority > best_cut[1]:
                best_cut = (pause_mid, priority, pause_start, pause_end)
        
        # Если найдена точка разреза
        if best_cut:
            segments.append((current_start, best_cut[0]))
            current_start = best_cut[0]
            
            # Пропускаем обработанные паузы
            while i < len(all_pauses) and all_pauses[i][1] <= best_cut[0]:
                i += 1
        else:
            # Если не найдена подходящая пауза, ищем любую доступную
            next_pause = None
            for j in range(i, len(all_pauses)):
                if all_pauses[j][0] > current_start:
                    next_pause = all_pauses[j]
                    break
            
            if next_pause:
                pause_mid = (next_pause[0] + next_pause[1]) // 2
                segments.append((current_start, pause_mid))
                current_start = pause_mid
                i = j + 1
            else:
                # Последний сегмент
                if len(audio) - current_start >= min_samples:
                    segments.append((current_start, len(audio)))
                break
    
    # Добавляем последний сегмент если остался
    if current_start < len(audio) and len(audio) - current_start >= min_samples:
        segments.append((current_start, len(audio)))
    
    # Второй проход - оптимизация
    segments = _optimize_segments(segments, sr, min_length, max_length)
    
    return segments


def _optimize_segments(segments: List[Tuple[int, int]], sr: int,
                      min_length: float, max_length: float) -> List[Tuple[int, int]]:
    """Оптимизирует сегменты - объединяет короткие, разделяет длинные."""
    
    min_samples = int(min_length * sr)
    max_samples = int(max_length * sr)
    
    optimized = []
    i = 0
    
    while i < len(segments):
        start, end = segments[i]
        duration = end - start
        
        # Если сегмент слишком короткий, пытаемся объединить со следующим
        if duration < min_samples and i + 1 < len(segments):
            next_start, next_end = segments[i + 1]
            combined_duration = next_end - start
            
            if combined_duration <= max_samples:
                optimized.append((start, next_end))
                i += 2  # Пропускаем следующий сегмент
                continue
        
        # Если сегмент слишком длинный, пытаемся разделить пополам
        if duration > max_samples:
            mid_point = start + duration // 2
            optimized.append((start, mid_point))
            optimized.append((mid_point, end))
        else:
            optimized.append((start, end))
        
        i += 1
    
    # Финальная фильтрация - удаляем сегменты короче минимума
    final_segments = []
    for start, end in optimized:
        if end - start >= min_samples:
            final_segments.append((start, end))
    
    return final_segments


def _save_segments(segments: List[Tuple[int, int]], audio: np.ndarray, sr: int,
                  output_dir: str, original_path: str) -> int:
    """Сохраняет сегменты в файлы с прогресс-баром."""
    
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    saved_count = 0

    for i, (start, end) in enumerate(tqdm(segments, desc="Сохранение сегментов", ncols=80)):
        segment_audio = audio[start:end]
        
        if len(segment_audio) > 0 and not np.all(segment_audio == 0):
            filename = f"{base_name}_segment_{i+1:04d}.wav"
            filepath = os.path.join(output_dir, filename)
            try:
                sf.write(filepath, segment_audio, sr)
                saved_count += 1
            except Exception as e:
                logging.warning(f"Не удалось сохранить сегмент {filename}: {e}")
    
    return saved_count


def _calculate_stats(segments: List[Tuple[int, int]], min_length: float, 
                    max_length: float, sr: int) -> dict:
    """Вычисляет статистику сегментации."""
    
    durations = [(end - start) / sr for start, end in segments]
    
    in_range = sum(1 for d in durations if min_length <= d <= max_length)
    too_short = sum(1 for d in durations if d < min_length)
    too_long = sum(1 for d in durations if d > max_length)
    
    return {
        "total_segments": len(segments),
        "in_range": in_range,
        "too_short": too_short,
        "too_long": too_long,
        "success_rate": (in_range / len(segments)) * 100 if segments else 0,
        "avg_duration": np.mean(durations) if durations else 0,
        "min_duration": min(durations) if durations else 0,
        "max_duration": max(durations) if durations else 0
    }


