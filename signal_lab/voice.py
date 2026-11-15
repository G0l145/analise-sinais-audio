"""Tratamento offline de fala: filtragem e redução conservadora de ruído estacionário.

Não realiza separação neural de fontes nem recuperação de áudio distorcido.
Blocos limitam a memória mesmo em gravações longas.
"""

import numpy as np
from scipy.ndimage import uniform_filter
from scipy.signal import butter, istft, sosfilt, stft

from .audio import Audio


def voice_filter_sos(sample_rate: int) -> np.ndarray:
    """Remove ruído subsônico e parte do chiado fora da faixa útil de fala."""
    highpass = butter(2, 75, btype="highpass", fs=sample_rate, output="sos")
    lowpass_hz = min(7200, 0.88 * (sample_rate / 2))
    lowpass = butter(2, lowpass_hz, btype="lowpass", fs=sample_rate, output="sos")
    return np.vstack((highpass, lowpass))


def reduce_stationary_noise(samples: np.ndarray, sample_rate: int, strength: float) -> np.ndarray:
    """Atenuação espectral moderada por blocos e estimativa de percentil baixo.

    A máscara jamais zera as frequências, para limitar artefatos em fala.
    A extensão contextual de cada bloco ameniza bordas sem armazenar toda a
    gravação no domínio da frequência.
    """
    if strength <= 0:
        return samples.copy()
    count, channels = samples.shape
    window = 512 if sample_rate <= 24_000 else 1024
    overlap = window * 3 // 4
    block = sample_rate * 12
    context = max(window, sample_rate // 4)
    output = np.empty_like(samples)

    for channel in range(channels):
        for start in range(0, count, block):
            stop = min(start + block, count)
            left = max(0, start - context)
            right = min(count, stop + context)
            segment = samples[left:right, channel]
            _, _, spectrum = stft(segment, fs=sample_rate, window="hann",
                                  nperseg=min(window, len(segment)),
                                  noverlap=min(overlap, max(0, len(segment) - 1)),
                                  boundary="zeros", padded=True)
            magnitude = np.abs(spectrum)
            noise = np.percentile(magnitude, 15, axis=1, keepdims=True)
            ratio = (noise / np.maximum(magnitude, 1e-12)) ** 2
            mask = np.clip(1.0 - 0.8 * strength * ratio,
                           max(0.25, 1.0 - strength), 1.0)
            mask = uniform_filter(mask, size=(3, 3), mode="nearest")
            _, restored = istft(spectrum * mask, fs=sample_rate, window="hann",
                                nperseg=min(window, len(segment)),
                                noverlap=min(overlap, max(0, len(segment) - 1)),
                                input_onesided=True, boundary=True)
            output[start:stop, channel] = restored[start - left:stop - left]
    return output


def clean_voice(audio: Audio, strength: float) -> tuple[np.ndarray, np.ndarray]:
    """Retorna amostras com ruído atenuado e SOS dos filtros lineares."""
    identity = np.array([[1., 0., 0., 1., 0., 0.]])
    if strength <= 0:
        return audio.samples.copy(), identity
    filters = voice_filter_sos(audio.sample_rate)
    # Retirar graves indesejados antes da estimativa de ruído.
    filtered = sosfilt(filters, audio.samples, axis=0)
    cleaned = reduce_stationary_noise(filtered, audio.sample_rate, strength)
    if not np.isfinite(cleaned).all():
        raise ValueError("O tratamento de voz produziu amostras inválidas.")
    return cleaned, filters
