"""Filtros adicionais de segunda ordem, com coeficientes normalizados em SOS.

Extensão opcional do laboratório; não altera o equalizador automático original.
"""
from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfilt, sosfreqz


@dataclass(frozen=True)
class FilterSpec:
    kind: str = "lowpass"  # lowpass, highpass, lowshelf, highshelf
    frequency_hz: float = 1000.0
    gain_db: float = 0.0
    q: float = 1 / np.sqrt(2)


def design_filter(spec: FilterSpec, sample_rate: int) -> np.ndarray:
    if not isinstance(sample_rate, int) or sample_rate < 8000 or sample_rate > 192000:
        raise ValueError("Taxa de amostragem inválida.")
    if spec.kind not in {"lowpass", "highpass", "lowshelf", "highshelf"}:
        raise ValueError("Tipo de filtro desconhecido.")
    if not np.isfinite([spec.frequency_hz, spec.gain_db, spec.q]).all():
        raise ValueError("Parâmetros não finitos.")
    if not 0 < spec.frequency_hz < sample_rate * 0.45:
        raise ValueError("Frequência fora da faixa segura abaixo de Nyquist.")
    if not 0.2 <= spec.q <= 5 or not -12 <= spec.gain_db <= 12:
        raise ValueError("Q ou ganho fora dos limites.")
    if spec.kind in {"lowpass", "highpass"}:
        return butter(2, spec.frequency_hz, btype="low" if spec.kind == "lowpass" else "high",
                      fs=sample_rate, output="sos")
    a = 10 ** (spec.gain_db / 40)
    w = 2 * np.pi * spec.frequency_hz / sample_rate
    cs = np.cos(w)
    sn = np.sin(w)
    alpha = sn / (2 * spec.q)
    root = 2 * np.sqrt(a) * alpha
    if spec.kind == "lowshelf":
        b = [a * ((a + 1) - (a - 1)*cs + root), 2*a*((a - 1) - (a + 1)*cs),
             a*((a + 1) - (a - 1)*cs - root)]
        d = [(a + 1) + (a - 1)*cs + root, -2*((a - 1) + (a + 1)*cs),
             (a + 1) + (a - 1)*cs - root]
    else:
        b = [a * ((a + 1) + (a - 1)*cs + root), -2*a*((a - 1) + (a + 1)*cs),
             a*((a + 1) + (a - 1)*cs - root)]
        d = [(a + 1) - (a - 1)*cs + root, 2*((a - 1) - (a + 1)*cs),
             (a + 1) - (a - 1)*cs - root]
    row = np.array([*b, *d], dtype=np.float64)
    return (row / row[3])[None, :]


def process_filter(samples: np.ndarray, sample_rate: int, spec: FilterSpec) -> np.ndarray:
    sos = design_filter(spec, sample_rate)
    samples = np.asarray(samples, dtype=np.float64)
    if samples.ndim not in (1, 2) or not np.isfinite(samples).all():
        raise ValueError("Amostras inválidas.")
    return sosfilt(sos, samples, axis=0)


def filter_response(spec: FilterSpec, sample_rate: int, points: int = 512):
    sos = design_filter(spec, sample_rate)
    freq, response = sosfreqz(sos, worN=points, fs=sample_rate)
    return freq, 20*np.log10(np.maximum(np.abs(response), 1e-12))
