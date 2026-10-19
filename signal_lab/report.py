"""Relatório auditável: unidades explícitas e JSON sem NaN ou infinito."""

from dataclasses import asdict
import json

import numpy as np
import pandas as pd

from . import __version__
from .analysis import CENTERS, EDGES, centered
from .dsp import Result
from .quality import compare_indicators

TARGET_NAMES = {
    "flat": "Mesma potência por banda de aproximadamente uma oitava",
    "gentle": "Potência por banda com inclinação de -1 dB por oitava",
    "reference": "Forma espectral de um áudio de referência",
}


def number(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def improvement_percent(result: Result) -> float | None:
    if result.error_before_db is None or result.error_after_db is None or result.error_before_db < 1e-9:
        return None
    return 100 * (1 - result.error_after_db / result.error_before_db)


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
        "spectral_indicators": compare_indicators(result.before, result.after),
        "metrics_before": result.before.stats,
        "metrics_after": result.after.stats,
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
