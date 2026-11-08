"""Gera WAVs sintéticos PCM16 para ensaio, sem dependências externas.

Uso: python scripts/gerar_audios_teste.py --out resultados/amostras-gravacao
Não captura o microfone e não sobrescreve diretórios existentes.
"""

import argparse
from array import array
import math
from pathlib import Path
import sys
import wave


def pcm16_wav(path: Path, rate: int, *, silence: bool = False) -> None:
    """Três segundos mono; tons em múltiplas bandas para avaliar os filtros."""
    samples = array("h")
    for index in range(3 * rate):
        t = index / rate
        # Envelope evita descontinuidade nas extremidades. Pico máximo < 0,7.
        envelope = min(1.0, t / 0.05, (3.0 - t) / 0.05)
        value = 0.0 if silence else envelope * (
            0.35 * math.sin(2 * math.pi * 125 * t)
            + 0.18 * math.sin(2 * math.pi * 500 * t)
            + 0.08 * math.sin(2 * math.pi * 2000 * t)
            + 0.04 * math.sin(2 * math.pi * 4000 * t)
        )
        samples.append(round(value * 32767))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("resultados/amostras-gravacao"))
    args = parser.parse_args()
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("O destino já existe. Escolha outra pasta para preservar os arquivos.")
    for rate in (16_000, 48_000):
        pcm16_wav(args.out / f"multibanda_{rate}Hz.wav", rate)
    pcm16_wav(args.out / "silencio_16000Hz.wav", 16_000, silence=True)
    print(f"Amostras sintéticas geradas em: {args.out.resolve()}")
    print("Teste primeiro os tons em volume baixo. Estes arquivos não validam o microfone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
