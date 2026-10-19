"""Indicadores complementares de qualidade, independentes da curva-alvo.

Grandezas espectrais estimadas pela PSD média da STFT (20 Hz a Nyquist).
Não equivalem a preferência musical nem garantem ausência de distorção.
"""

import numpy as np

from .analysis import Analysis


def spectral_indicators(analysis: Analysis) -> dict[str, float | None]:
    """Calcula indicadores de distribuição espectral com custo linear nos bins."""
    freq = np.asarray(analysis.frequencies, dtype=np.float64)
    psd = np.asarray(analysis.psd, dtype=np.float64)
    mask = (freq >= 20) & np.isfinite(freq) & np.isfinite(psd) & (psd >= 0)
    bands = freq[mask]
    energy = psd[mask]
    total = float(np.sum(energy))
    if bands.size < 2 or total <= 1e-24:
        return {
            "spectral_centroid_hz": None,
            "spectral_rolloff_85_hz": None,
            "spectral_flatness": None,
            "spectral_spread_hz": None,
            "crest_factor_db": _crest_factor(analysis),
        }

    centroid = float(np.dot(bands, energy) / total)
    spread = float(np.sqrt(np.dot((bands - centroid) ** 2, energy) / total))
    rolloff = float(bands[min(len(bands) - 1,
                             int(np.searchsorted(np.cumsum(energy), 0.85 * total)))])
    mean = float(np.mean(energy))
    # Flatness é a média geométrica sobre a aritmética. Um piso absoluto
    # alteraria essa razão ao atenuar o sinal, mesmo sem mudar sua forma.
    # Bins exatamente nulos implicam média geométrica zero.
    if np.any(energy == 0):
        flatness = 0.0
    else:
        flatness = float(np.exp(np.mean(np.log(energy / mean))))
        flatness = min(1.0, max(0.0, flatness))
    return {
        "spectral_centroid_hz": centroid,
        "spectral_rolloff_85_hz": rolloff,
        "spectral_flatness": flatness,
        "spectral_spread_hz": spread,
        "crest_factor_db": _crest_factor(analysis),
    }


def _crest_factor(analysis: Analysis) -> float | None:
    peak = analysis.stats.get("sample_peak_dbfs")
    rms = analysis.stats.get("rms_dbfs")
    return float(peak - rms) if peak is not None and rms is not None else None


def compare_indicators(before: Analysis, after: Analysis) -> dict:
    """Medições e variações (depois - antes), sem qualificá-las como melhora."""
    previous = spectral_indicators(before)
    current = spectral_indicators(after)
    delta = {
        key: (current[key] - previous[key]
              if previous[key] is not None and current[key] is not None else None)
        for key in previous
    }
    return {"before": previous, "after": current, "difference": delta}
