import os
import numpy as np
import librosa
import soundfile as sf
from scipy.ndimage import binary_opening
import torch

# === Загрузка Silero VAD (один раз при старте) ===
def get_silero_vad_model():
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False
    )
    (get_speech_timestamps, _, _, _, _) = utils
    return get_speech_timestamps, model

# Кэшируем модель
_silero_cache = None

def segment_audio(
    input_wav_path,
    output_dir,
    min_length=1.5,
    max_length=12.0,
    min_silence_duration=0.3,
    speech_pad=0.05,  # небольшой отступ от границы речи
    frame_length=512,
    hop_length=160,   # 10 мс при 16 кГц
    max_extension=1.5,
    allow_short_final=True,
    debug=False,
):
    """
    Высококачественная сегментация аудио для TTS с использованием Silero VAD.
    Без транскрипции. Оптимизировано под одного говорящего.

    Параметры:
        input_wav_path: путь к WAV (16 кГц, моно)
        output_dir: папка для сегментов
        min_length: мин. длительность сегмента (сек)
        max_length: макс. длительность (сек)
        min_silence_duration: мин. пауза для разреза (сек)
        speech_pad: отступ от начала/конца речи (сек)
        max_extension: на сколько можно выйти за max_length, чтобы найти паузу
        debug: сохранить график
    """
    global _silero_cache

    # Загружаем аудио
    try:
        y, sr = librosa.load(input_wav_path, sr=16000, mono=True)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load audio: {str(e)}"}

    if sr != 16000:
        return {"status": "error", "message": "Audio must be 16kHz."}

    total_duration = len(y) / sr

    # === Загружаем Silero VAD ===
    if _silero_cache is None:
        try:
            _silero_cache = get_silero_vad_model()
        except Exception as e:
            return {"status": "error", "message": f"Failed to load Silero VAD: {str(e)}"}
    get_speech_timestamps, model = _silero_cache

    # Подготовка аудио для VAD (в формате, который он понимает)
    # VAD работает на 16 кГц — идеально
    wav_tensor = torch.from_numpy(y).float().unsqueeze(0)  # [1, T]

    # Получаем временные метки активной речи
    try:
        speech_segments = get_speech_timestamps(
            wav_tensor,
            model,
            threshold=0.5,
            min_silence_duration_ms=int(min_silence_duration * 1000),
            speech_pad_ms=int(speech_pad * 1000)
        )
    except Exception as e:
        return {"status": "error", "message": f"VAD processing failed: {str(e)}"}

    # Конвертируем в список словарей в секундах
    active_intervals = [
        {"start": s["start"] / 16000.0, "end": s["end"] / 16000.0}
        for s in speech_segments
    ]

    if not active_intervals:
        return {"status": "warning", "message": "No speech detected", "segments_count": 0}

    # === Слияние близких интервалов (если пауза < min_silence_duration) ===
    merged = []
    current = active_intervals[0]
    for next_seg in active_intervals[1:]:
        if next_seg["start"] - current["end"] < min_silence_duration:
            current["end"] = next_seg["end"]
        else:
            merged.append(current)
            current = next_seg
    merged.append(current)

    # === Основной цикл: формируем сегменты ===
    os.makedirs(output_dir, exist_ok=True)
    chunks = []
    durations = []
    saved = 0
    current_time = 0.0
    segment_idx = 1

    split_points = []

    while current_time < total_duration:
        start_time = current_time
        min_end_time = start_time + min_length
        max_end_time = start_time + max_length
        hard_end_time = min(max_end_time, total_duration)
        search_end_time = min(max_end_time + max_extension, total_duration)

        # Ищем следующую **длинную паузу** после min_end_time
        cut_time = None

        for interval in merged:
            # Если интервал начинается после min_end_time и в пределах max_end + extension
            if interval["start"] > min_end_time and interval["start"] <= search_end_time:
                # Это кандидат на разрез
                silence_start = interval["start"]
                # Проверим, что пауза перед ним достаточно длинная
                prev_end = current_time
                for prev in merged:
                    if prev["end"] < silence_start:
                        prev_end = max(prev_end, prev["end"])
                if silence_start - prev_end >= min_silence_duration:
                    cut_time = silence_start
                    break

        # Если не нашли паузу в расширенной зоне — режем на hard_end
        if cut_time is None:
            cut_time = hard_end_time

        # Убедимся, что сегмент не слишком короткий
        seg_duration = cut_time - start_time
        if seg_duration < min_length:
            if cut_time >= total_duration and allow_short_final:
                cut_time = total_duration
            else:
                # Принудительно тянем до max_length, если возможно
                cut_time = start_time + max_length
                cut_time = min(cut_time, total_duration)
                seg_duration = cut_time - start_time
                if seg_duration < min_length:
                    if allow_short_final and start_time < total_duration:
                        cut_time = total_duration
                    else:
                        break  # ничего не остаётся

        # Защита от зацикливания
        if cut_time <= start_time + 1e-3:
            cut_time = min(start_time + 0.2, total_duration)
            if cut_time <= start_time:
                break

        # Извлекаем аудио
        start_sample = int(start_time * sr)
        end_sample = int(cut_time * sr)
        segment = y[start_sample:end_sample]

        if len(segment) == 0:
            break

        # Сохраняем
        chunk = {
            "start": start_time,
            "end": cut_time,
            "duration": cut_time - start_time,
            "samples": segment
        }
        chunks.append(chunk)
        durations.append(chunk["duration"])
        split_points.append(cut_time)

        # Сохраняем файл
        filename = f"segment_{saved + 1:04d}.wav"
        filepath = os.path.join(output_dir, filename)
        sf.write(filepath, segment, sr, subtype='PCM_16')
        saved += 1

        # Переход
        current_time = cut_time

        if current_time >= total_duration - 1e-3:
            break

    # === Debug: график ===
    if debug:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(16, 8), sharex=True)

        t_audio = np.arange(len(y)) / sr
        ax[0].plot(t_audio, y, color='lightgray', linewidth=0.7)
        for sp in split_points:
            ax[0].axvline(sp, color='red', linestyle='--', alpha=0.8, linewidth=1)
        for seg in merged:
            ax[0].axvspan(seg["start"], seg["end"], color='green', alpha=0.1)
        ax[0].set_title("Audio waveform (green = speech, red = split)")
        ax[0].set_ylabel("Amplitude")

        # RMS для контекста
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        ax[1].plot(t_rms, librosa.amplitude_to_db(rms, ref=1.0), color='blue', alpha=0.7, linewidth=0.8)
        for sp in split_points:
            ax[1].axvline(sp, color='red', linestyle='--', alpha=0.8)
        for seg in merged:
            ax[1].axvspan(seg["start"], seg["end"], color='green', alpha=0.1)
        ax[1].set_title("RMS (dB) and speech regions")
        ax[1].set_xlabel("Time (s)")
        ax[1].set_ylabel("RMS (dB)")

        plt.xlim(0, total_duration)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "segmentation_debug.png"), dpi=150)
        plt.close()

    # === Статистика ===
    stats = {
        "total_chunks": len(chunks),
        "saved": saved,
        "avg_duration": float(np.mean(durations)) if durations else 0,
        "min_duration": float(np.min(durations)) if durations else 0,
        "max_duration": float(np.max(durations)) if durations else 0,
        "allow_short_final": allow_short_final,
    }

    return {
        "status": "success",
        "segments_count": saved,
        "stats": stats,
        "split_points": split_points
    }
