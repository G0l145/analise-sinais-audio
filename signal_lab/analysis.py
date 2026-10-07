"""STFT em lotes, potência média por canal e bandas de aproximadamente uma oitava."""

from dataclasses import dataclass
import warnings

import numpy as np
from scipy.fft import rfft
from scipy.signal import get_window
import pyloudnorm as pyln

from .audio import Audio

CENTERS = np.array([31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], dtype=float)
EDGES = np.r_[CENTERS[0] / np.sqrt(2), np.sqrt(CENTERS[:-1] * CENTERS[1:]), CENTERS[-1] * np.sqrt(2)]
EPS = 1e-20


def finite_db(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def metrics(audio: Audio) -> dict:
    samples = audio.samples
    rms = float(np.sqrt(np.mean(samples ** 2)))
    peak = float(np.max(np.abs(samples)))
    integrated = None
    if audio.duration >= 0.4 and rms > 1e-12:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            integrated = finite_db(pyln.Meter(audio.sample_rate).integrated_loudness(samples))
    return {
        "rms_linear": rms,
        "rms_dbfs": float(20 * np.log10(rms)) if rms > 0 else None,
        "sample_peak_dbfs": float(20 * np.log10(peak)) if peak > 0 else None,
        "integrated_lufs": integrated,
        "samples_at_or_above_full_scale": int(np.count_nonzero(np.abs(samples) >= 1.0)),
    }


@dataclass
class Analysis:
    frequencies: np.ndarray
    psd: np.ndarray
    band_power: np.ndarray
    band_db: np.ndarray
    usable: np.ndarray
    spectrogram_db: np.ndarray
    frame_times: np.ndarray
    n_fft: int
    hop: int
    frames: int
    stats: dict


def band_powers(frequencies: np.ndarray, psd: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    df = frequencies[1] - frequencies[0]
    values = np.zeros(10)
    usable = np.zeros(10, dtype=bool)
    for i, center in enumerate(CENTERS):
        bins = (frequencies >= EDGES[i]) & (frequencies < min(EDGES[i + 1], sample_rate / 2))
        # Margem abaixo de Nyquist para evitar filtros mal condicionados.
        if center < sample_rate * 0.45 and np.any(bins):
            values[i] = float(np.sum(psd[bins]) * df)
            usable[i] = True
    return values, usable


def analyze(audio: Audio, fft_size: int = 8192, max_columns: int = 360) -> Analysis:
    """Média de potência STFT de TODAS as janelas completas, sem somar canais em amplitude.

    Hann periódica, 50% de sobreposição, PSD unilateral em amplitude²/Hz.
    Apenas a imagem é subamostrada no tempo; a potência usa todas as janelas.
    """
    n = len(audio.samples)
    if fft_size < 2 or max_columns < 1:
        raise ValueError("FFT e quantidade de colunas devem ser positivas.")
    n_fft = min(fft_size, 2 ** int(np.floor(np.log2(n))))
    hop = max(1, n_fft // 2)
    window = get_window("hann", n_fft, fftbins=True)
    norm = audio.sample_rate * np.sum(window ** 2)
    frames = 1 + (n - n_fft) // hop
    view = np.lib.stride_tricks.sliding_window_view(audio.samples, n_fft, axis=0)[::hop]
    selected = np.unique(np.linspace(0, frames - 1, min(frames, max_columns)).astype(int))
    spectrum_sum = np.zeros(n_fft // 2 + 1)
    image = np.empty((n_fft // 2 + 1, len(selected)), dtype=np.float32)
    for start in range(0, frames, 32):
        segment = view[start:start + 32] * window
        transformed = rfft(segment, axis=-1)
        power = np.abs(transformed) ** 2 / norm
        if n_fft % 2 == 0:
            power[..., 1:-1] *= 2
        else:
            power[..., 1:] *= 2
        mean_channels = power.mean(axis=1)
        spectrum_sum += mean_channels.sum(axis=0)
        chosen = (selected >= start) & (selected < start + len(segment))
        if np.any(chosen):
            image[:, chosen] = (10 * np.log10(np.maximum(mean_channels[selected[chosen] - start], EPS))).T
    psd = spectrum_sum / frames
    frequencies = np.fft.rfftfreq(n_fft, 1 / audio.sample_rate)
    powers, physical = band_powers(frequencies, psd, audio.sample_rate)
    bands = 10 * np.log10(np.maximum(powers, EPS))
    # Não propor ganho onde só há silêncio ou energia desprezível.
    usable = physical & (powers > max(EPS, float(np.max(powers)) * 1e-7))
    return Analysis(
        frequencies, psd, powers, bands, usable, image,
        (selected * hop + n_fft / 2) / audio.sample_rate,
        n_fft, hop, frames, metrics(audio),
    )


def centered(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    result = np.full(len(values), np.nan)
    if np.any(mask):
        result[mask] = values[mask] - np.mean(values[mask])
    return result
