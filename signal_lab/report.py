"""Relatório auditável: unidades explícitas e JSON sem NaN ou infinito."""

from dataclasses import asdict
import json

import numpy as np
import pandas as pd

from . import __version__
from .analysis import CENTERS, EDGES, centered
from .dsp import Result

TARGET_NAMES = {
    "flat": "Mesma potência por banda de aproximadamente uma oitava",
    "gentle": "Potência por banda com inclinação de -1 dB por oitava",
    "reference": "Forma espectral de um áudio de referência",
    "voice": "Tratamento de fala: redução de ruído e realce da faixa de presença",
}


def number(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def improvement_percent(result: Result) -> float | None:
    if result.error_before_db is None or result.error_after_db is None or result.error_before_db < 1e-9:
        return None
    return 100 * (1 - result.error_after_db / result.error_before_db)



def _level_dbfs(power: float) -> float | None:
    """Converte potência normalizada em dBFS; silêncio não possui nível finito."""
    return float(10 * np.log10(power)) if power > 0 else None


def voice_measurements(result: Result) -> dict:
    """Medições objetivas do modo vocal, sem atribuir pontuação de inteligibilidade.

    As mesmas janelas, escolhidas pelos 20% menores níveis RMS da ENTRADA,
    são comparadas na saída. Podem conter fala baixa, não apenas ruído.
    """
    if result.settings.target != "voice":
        raise ValueError("As medições de voz exigem o modo voice.")
    original = result.original.samples
    processed = result.processed.samples
    window = min(len(original), max(1, round(result.original.sample_rate * 0.1)))
    count = len(original) // window
    before_power = np.mean(original[:count * window].reshape(count, window, -1) ** 2, axis=(1, 2))
    after_power = np.mean(processed[:count * window].reshape(count, window, -1) ** 2, axis=(1, 2))
    selected_count = max(1, int(np.ceil(count * 0.2)))
    selected = np.argsort(before_power, kind="stable")[:selected_count]
    low_before = _level_dbfs(float(np.mean(before_power[selected])))
    low_after = _level_dbfs(float(np.mean(after_power[selected])))
    rms_before = result.before.stats["rms_dbfs"]
    rms_after = result.after.stats["rms_dbfs"]
    return {
        "rms_before_dbfs": rms_before,
        "rms_after_dbfs": rms_after,
        "rms_change_db": (float(rms_after - rms_before)
                          if rms_before is not None and rms_after is not None else None),
        "low_energy_before_dbfs": low_before,
        "low_energy_after_dbfs": low_after,
        "low_energy_attenuation_db": (float(low_before - low_after)
                                      if low_before is not None and low_after is not None else None),
        "low_energy_window_duration_ms": 1000 * window / result.original.sample_rate,
        "low_energy_selected_windows": selected_count,
        "low_energy_total_windows": count,
        "low_energy_fraction": 0.2,
    }


def band_table(result: Result) -> pd.DataFrame:
    before = centered(result.before.band_db, result.mask)
    after = centered(result.after.band_db, result.mask)
    return pd.DataFrame({
        "Centro (Hz)": CENTERS,
        "Banda usada": result.mask,
        "Antes relativo (dB)": before,
        "Alvo relativo (dB)": result.target_db,
        "Depois relativo (dB)": after,
        "Ganho do filtro (dB)": result.gains_db,
    })


def make_report(result: Result) -> dict:
    bands = []
    before = centered(result.before.band_db, result.mask)
    after = centered(result.after.band_db, result.mask)
    for i, center in enumerate(CENTERS):
        bands.append({
            "center_hz": float(center),
            "low_hz": float(EDGES[i]),
            "high_hz": float(min(EDGES[i + 1], result.original.sample_rate / 2)) if EDGES[i] < result.original.sample_rate / 2 else None,
            "used": bool(result.mask[i]),
            "before_power_fs_squared": float(result.before.band_power[i]),
            "after_power_fs_squared": float(result.after.band_power[i]),
            "before_relative_db": number(before[i]),
            "target_relative_db": number(result.target_db[i]),
            "after_relative_db": number(after[i]),
            "filter_gain_db": float(result.gains_db[i]),
        })
    covered = result.before.n_fft + (result.before.frames - 1) * result.before.hop
    return {
        "schema_version": "1.0",
        "software": {"name": "Sinal", "version": __version__},
        "audio": {
            "name": result.original.name,
            "sample_rate_hz": result.original.sample_rate,
            "channels": result.original.channels,
            "samples_per_channel": len(result.original.samples),
            "duration_seconds": result.original.duration,
        },
        "settings": asdict(result.settings),
        "target_description": TARGET_NAMES[result.settings.target],
        "reference_name": result.reference_name,
        "analysis": {
            "method": "Mean one-sided STFT power density, averaged across channels",
            "window": "periodic Hann",
            "fft_size": result.before.n_fft,
            "hop_samples": result.before.hop,
            "frequency_step_hz": result.original.sample_rate / result.before.n_fft,
            "complete_frames": result.before.frames,
            "tail_samples_not_analyzed": len(result.original.samples) - covered,
            "spectrogram_display_columns": len(result.before.frame_times),
        },
        "metrics_before": result.before.stats,
        "metrics_after": result.after.stats,
        "voice_measurements": voice_measurements(result) if result.settings.target == "voice" else None,
        "relative_shape_rmse_before_db": result.error_before_db,
        "relative_shape_rmse_after_db": result.error_after_db,
        "relative_shape_rmse_reduction_percent": improvement_percent(result),
        "global_peak_attenuation_db": result.attenuation_db,
        "bands": bands,
        "sos_coefficients": result.sos.tolist(),
        "notes": result.notes,
    }


def json_bytes(result: Result) -> bytes:
    return json.dumps(make_report(result), ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def csv_bytes(result: Result) -> bytes:
    return band_table(result).to_csv(index=False, sep=";", float_format="%.6f").encode("utf-8-sig")
