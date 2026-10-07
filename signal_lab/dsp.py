"""Equalização IIR em SOS com ganhos limitados e validação da aproximação à curva-alvo."""

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import sosfilt, sosfreqz

from .audio import Audio
from .analysis import Analysis, CENTERS, analyze, centered


@dataclass(frozen=True)
class Settings:
    target: str = "flat"  # flat, gentle ou reference
    strength: float = 0.65
    max_gain_db: float = 6.0
    q: float = 1.4
    ceiling_dbfs: float = -1.0

    def __post_init__(self):
        numeric = [self.strength, self.max_gain_db, self.q, self.ceiling_dbfs]
        if not np.isfinite(numeric).all():
            raise ValueError("Os parâmetros devem ser finitos.")
        if self.target not in {"flat", "gentle", "reference"}:
            raise ValueError("Curva-alvo desconhecida.")
        if not 0 <= self.strength <= 1 or not 0 <= self.max_gain_db <= 6:
            raise ValueError("A intensidade deve estar entre 0 e 1 e o limite entre 0 e 6 dB.")
        if not 0.2 <= self.q <= 5 or not -24 <= self.ceiling_dbfs < 0:
            raise ValueError("Q ou teto de pico fora do intervalo permitido.")


def peaking_sos(center: float, gain_db: float, rate: int, q: float = 1.4) -> np.ndarray:
    """Peaking EQ de Robert Bristow-Johnson, Audio EQ Cookbook/W3C."""
    if not np.isfinite([center, gain_db, rate, q]).all() or rate <= 0 or q <= 0 or not 0 < center < rate / 2:
        raise ValueError("Frequência, taxa, ganho ou Q inválidos para o filtro.")
    amplitude = 10 ** (gain_db / 40)
    omega = 2 * np.pi * center / rate
    alpha = np.sin(omega) / (2 * q)
    cosine = np.cos(omega)
    row = np.array([
        1 + alpha * amplitude, -2 * cosine, 1 - alpha * amplitude,
        1 + alpha / amplitude, -2 * cosine, 1 - alpha / amplitude,
    ])
    return row / row[3]


def build_sos(gains: np.ndarray, rate: int, q: float = 1.4) -> np.ndarray:
    gains = np.asarray(gains)
    if gains.shape != (10,) or not np.isfinite(gains).all():
        raise ValueError("São necessários dez ganhos finitos.")
    rows = [peaking_sos(center, float(gain), rate, q)
            for center, gain in zip(CENTERS, gains)
            if center < rate * 0.45 and abs(gain) > 1e-10]
    return np.asarray(rows) if rows else np.array([[1., 0., 0., 1., 0., 0.]])


def smooth_gains(delta: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Média local 1/4, 1/2, 1/4, renormalizada se um vizinho estiver indisponível."""
    result = np.zeros(10)
    for i in np.flatnonzero(mask):
        indices = np.arange(max(0, i - 1), min(10, i + 2))
        weights = np.where(indices == i, 0.5, 0.25) * mask[indices]
        result[i] = np.sum(delta[indices] * weights) / np.sum(weights)
    return result


def shape_error(analysis: Analysis, target: np.ndarray, mask: np.ndarray) -> float | None:
    if np.count_nonzero(mask) < 2:
        return None
    measured = centered(analysis.band_db, mask)
    desired = centered(target, mask)
    return float(np.sqrt(np.mean((measured[mask] - desired[mask]) ** 2)))


@dataclass
class Result:
    original: Audio
    processed: Audio
    before: Analysis
    after: Analysis
    settings: Settings
    target_db: np.ndarray
    mask: np.ndarray
    gains_db: np.ndarray
    sos: np.ndarray
    attenuation_db: float
    error_before_db: float | None
    error_after_db: float | None
    reference_name: str | None = None
    notes: list[str] = field(default_factory=list)


def equalize(audio: Audio, settings: Settings | None = None, reference: Audio | None = None) -> Result:
    settings = settings or Settings()
    before = analyze(audio)
    mask = before.usable.copy()
    target = np.zeros(10)
    notes = []
    reference_name = None
    if settings.target == "gentle":
        target = -np.log2(CENTERS / 1000)  # -1 dB por oitava de energia integrada.
    elif settings.target == "reference":
        if reference is None:
            raise ValueError("Selecione um áudio de referência para esse modo.")
        ref_analysis = analyze(reference)
        if not np.any(ref_analysis.usable):
            raise ValueError("A referência não contém energia suficiente para orientar a equalização.")
        target = ref_analysis.band_db.copy()
        mask &= ref_analysis.usable
        reference_name = reference.name
    delta = np.zeros(10)
    if np.count_nonzero(mask) >= 2:
        measured = centered(before.band_db, mask)
        desired = centered(target, mask)
        delta[mask] = desired[mask] - measured[mask]
    else:
        notes.append("Menos de duas bandas mensuráveis: equalização espectral desativada.")
        mask[:] = False
    gains = np.clip(smooth_gains(delta, mask) * settings.strength, -settings.max_gain_db, settings.max_gain_db)
    original_error = shape_error(before, target, mask)
    best = None
    # A sobreposição dos filtros pode afastar a saída do alvo. Medir antes de aceitar.
    for factor in (1.0, 0.5, 0.0):
        trial_gains = gains * factor
        sos = build_sos(trial_gains, audio.sample_rate, settings.q)
        samples = sosfilt(sos, audio.samples, axis=0)
        if not np.isfinite(samples).all():
            raise ValueError("O processamento produziu valores não finitos.")
        peak = float(np.max(np.abs(samples)))
        ceiling = 10 ** (settings.ceiling_dbfs / 20)
        scale = min(1.0, ceiling / peak) if peak else 1.0
        processed = Audio(samples * scale, audio.sample_rate, f"{audio.name}_equalizado")
        after = analyze(processed)
        error = shape_error(after, target, mask)
        candidate = (processed, after, trial_gains, sos, float(20 * np.log10(scale)), error, factor)
        if best is None or (error is not None and error < best[5]):
            best = candidate
        if original_error is None or error <= original_error + 1e-8:
            break
    processed, after, gains, sos, attenuation, error, factor = best
    if factor != 1.0:
        notes.append("A correção foi reduzida após medir a sobreposição entre os filtros.")
    if attenuation < -1e-8:
        notes.append(f"Atenuação global de {attenuation:.2f} dB para respeitar o teto de pico de amostras.")
    if np.any(~mask):
        notes.append("Bandas indisponíveis ou sem energia relevante não recebem ganho.")
    if before.stats["samples_at_or_above_full_scale"]:
        notes.append("A entrada contém amostras em ou acima de 0 dBFS; a equalização não recupera distorção preexistente.")
    notes.append("O teto usa pico de amostras; não constitui um limitador de true peak.")
    return Result(audio, processed, before, after, settings, centered(target, mask), mask,
                  gains, sos, attenuation, original_error, error, reference_name, notes)


def frequency_response(result: Result, points: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    frequencies, transfer = sosfreqz(result.sos, worN=points, fs=result.original.sample_rate)
    return frequencies, 20 * np.log10(np.maximum(np.abs(transfer), 1e-12))
