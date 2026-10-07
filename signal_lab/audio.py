"""Leitura controlada de áudio e exportação WAV sem alterar o arquivo original."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import soundfile as sf

MAX_SECONDS = 300
MAX_FRAMES = 14_400_000  # Até cinco minutos estéreo a 48 kHz.
MAX_BYTES = 50 * 1024 * 1024


@dataclass
class Audio:
    samples: np.ndarray  # (amostras, canais); ponto flutuante, escala digital.
    sample_rate: int
    name: str = "audio"

    def __post_init__(self):
        if isinstance(self.sample_rate, bool) or not isinstance(self.sample_rate, (int, np.integer)):
            raise ValueError("A taxa de amostragem deve ser um número inteiro.")
        if not 8_000 <= self.sample_rate <= 96_000:
            raise ValueError("Use uma taxa de amostragem entre 8 e 96 kHz.")
        x = np.asarray(self.samples, dtype=np.float64)
        if x.ndim == 1:
            x = x[:, None]
        if x.ndim != 2 or x.shape[1] not in (1, 2) or len(x) < 2:
            raise ValueError("O áudio deve conter pelo menos duas amostras e ser mono ou estéreo.")
        if len(x) > MAX_FRAMES or len(x) / self.sample_rate > MAX_SECONDS:
            raise ValueError("O MVP aceita até 300 segundos e 14,4 milhões de amostras por canal.")
        if not np.isfinite(x).all():
            raise ValueError("O áudio contém valores inválidos (NaN ou infinito).")
        self.samples = np.ascontiguousarray(x)

    @property
    def duration(self):
        return len(self.samples) / self.sample_rate

    @property
    def channels(self):
        return self.samples.shape[1]


def read_audio(source: bytes | str | Path, name: str | None = None) -> Audio:
    """Inspeciona o cabeçalho antes da decodificação para limitar memória."""
    if isinstance(source, bytes):
        if len(source) > MAX_BYTES:
            raise ValueError("O arquivo ultrapassa o limite de 50 MB.")
        stream = BytesIO(source)
        default_name = "audio_enviado"
    else:
        path = Path(source)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("O arquivo ultrapassa o limite de 50 MB.")
        stream = path
        default_name = path.name
    try:
        with sf.SoundFile(stream) as handle:
            if handle.channels not in (1, 2):
                raise ValueError("Este MVP aceita arquivos mono ou estéreo.")
            if not 8_000 <= handle.samplerate <= 96_000:
                raise ValueError("Use uma taxa de amostragem entre 8 e 96 kHz.")
            if handle.frames > MAX_FRAMES or handle.frames / handle.samplerate > MAX_SECONDS:
                raise ValueError("O áudio excede o limite de duração ou de amostras do MVP.")
            samples = handle.read(dtype="float64", always_2d=True)
            rate = handle.samplerate
    except (sf.LibsndfileError, RuntimeError) as exc:
        raise ValueError("Não foi possível ler o áudio. Use WAV/FLAC ou um MP3 compatível com libsndfile.") from exc
    return Audio(samples, rate, name or default_name)


def wav_bytes(audio: Audio, subtype: str = "PCM_24") -> bytes:
    if np.max(np.abs(audio.samples)) >= 1.0:
        raise ValueError("A exportação PCM exige amostras abaixo de 0 dBFS. Aplique proteção de pico.")
    stream = BytesIO()
    sf.write(stream, audio.samples, audio.sample_rate, format="WAV", subtype=subtype)
    return stream.getvalue()


def safe_preview(audio: Audio, ceiling_dbfs: float = -1.0) -> Audio:
    ceiling = 10 ** (ceiling_dbfs / 20)
    peak = float(np.max(np.abs(audio.samples)))
    scale = min(1.0, ceiling / peak) if peak else 1.0
    return Audio(audio.samples * scale, audio.sample_rate, audio.name)


def matched_pair(before: Audio, after: Audio) -> tuple[Audio, Audio]:
    """Atenua até o menor RMS; não altera o resultado exportado."""
    if before.sample_rate != after.sample_rate or before.samples.shape != after.samples.shape:
        raise ValueError("A comparação exige a mesma taxa de amostragem, duração e canais.")
    rms_a = float(np.sqrt(np.mean(before.samples ** 2)))
    rms_b = float(np.sqrt(np.mean(after.samples ** 2)))
    if min(rms_a, rms_b) <= 1e-12:
        return safe_preview(before), safe_preview(after)
    common = min(rms_a, rms_b)
    a = before.samples * common / rms_a
    b = after.samples * common / rms_b
    maximum = max(float(np.max(np.abs(a))), float(np.max(np.abs(b))))
    scale = min(1.0, 10 ** (-1 / 20) / maximum)
    return Audio(a * scale, before.sample_rate, before.name), Audio(b * scale, after.sample_rate, after.name)
