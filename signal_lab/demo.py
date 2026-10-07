"""Trecho musical sintético original; referência conhecida para um experimento repetível."""

import numpy as np
from scipy.signal import sosfilt

from .audio import Audio
from .dsp import build_sos


def demo_pair(duration: float = 12.0, rate: int = 44100, seed: int = 42) -> tuple[Audio, Audio]:
    if not np.isfinite(duration) or not 0.5 <= duration <= 30:
        raise ValueError("A demonstração aceita de 0,5 a 30 segundos.")
    rng = np.random.default_rng(seed)
    t = np.arange(int(duration * rate)) / rate
    base = np.zeros_like(t)
    beat = 0.5
    bass_notes = [65.406, 82.407, 87.307, 73.416]
    lead_notes = [261.626, 329.628, 391.995, 523.251, 440.0, 391.995, 329.628, 293.665]
    for k, start in enumerate(np.arange(0, duration, beat)):
        index = (t >= start) & (t < start + beat)
        u = t[index] - start
        bass = bass_notes[(k // 4) % len(bass_notes)]
        base[index] += 0.32 * np.sin(2 * np.pi * bass * u) * np.exp(-u * 3)
        base[index] += 0.14 * np.sin(2 * np.pi * lead_notes[k % len(lead_notes)] * u) * np.exp(-u * 6)
        base[index] += 0.22 * np.sin(2 * np.pi * (48 * u + 35 * (1 - np.exp(-u * 25)) / 25)) * np.exp(-u * 20)
        hat = rng.normal(size=len(u))
        base[index] += 0.035 * np.r_[0., np.diff(hat)] * np.exp(-u * 50)
        if k % 2:
            base[index] += 0.055 * rng.normal(size=len(u)) * np.exp(-u * 18)
    # Fundo 1/f para que todas as bandas tenham energia observável no experimento.
    white = rng.normal(size=len(t))
    frequencies = np.fft.rfftfreq(len(t), 1 / rate)
    pink = np.fft.irfft(np.fft.rfft(white) / np.sqrt(np.maximum(frequencies, 20)), n=len(t))
    pink /= max(float(np.std(pink)), 1e-12)
    base += 0.015 * pink
    fade = np.minimum(1, np.minimum(t / 0.02, (duration - t) / 0.04))
    base *= np.maximum(0, fade)
    stereo = np.column_stack([base, 0.94 * base + 0.006 * pink * fade])
    stereo *= 0.70 / np.max(np.abs(stereo))
    reference = Audio(stereo, rate, "referencia_sintetica.wav")
    tilt = np.array([4., 6., 5., 2., 0., -2., -4., -5., -4., -3.])
    biased = sosfilt(build_sos(tilt, rate), stereo, axis=0)
    biased *= 0.70 / np.max(np.abs(biased))
    return Audio(biased, rate, "demo_com_graves_realçados.wav"), reference
