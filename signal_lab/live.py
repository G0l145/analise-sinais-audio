"""Demonstração opcional de áudio em tempo real por loopback entrada -> saída.

Instale a dependência opcional sounddevice somente na máquina local. 
Use fones de ouvido e volume baixo para reduzir o risco de microfonia.
Nao é adequado executar no Codespaces (servidor sem dispositivo de áudio).
"""
import argparse

import numpy as np

from .advanced_filters import FilterSpec, design_filter
from .streaming import StreamingEQ


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sinal: demonstração local ao vivo")
    parser.add_argument("--enable-audio", action="store_true",
                        help="Autorização explícita para abrir entrada e saída de áudio")
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--rate", type=int, default=44100)
    parser.add_argument("--channels", type=int, choices=[1, 2], default=1)
    parser.add_argument("--blocksize", type=int, default=512)
    parser.add_argument("--filter", choices=["lowpass", "highpass", "lowshelf", "highshelf"], default="lowpass")
    parser.add_argument("--cutoff", type=float, default=3000)
    parser.add_argument("--gain", type=float, default=0)
    parser.add_argument("--input-device", type=int, default=None)
    parser.add_argument("--output-device", type=int, default=None)
    args = parser.parse_args(argv)
    if not args.enable_audio:
        parser.error("Por segurança, inclua --enable-audio para ativar microfone e saída.")
    if not (0 < args.seconds <= 60) or not (128 <= args.blocksize <= 4096):
        parser.error("Duração deve estar entre 0 e 60 s; bloco entre 128 e 4096 amostras.")
    if args.rate not in (44100, 48000):
        parser.error("Use 44100 ou 48000 Hz.")
    try:
        import sounddevice as sd
    except ImportError as exc:
        parser.error("Dependência ausente: instale sounddevice no computador local.")
    try:
        sos = design_filter(FilterSpec(args.filter, args.cutoff, args.gain), args.rate)
        engine = StreamingEQ(sos, args.channels)
        # Callback usa blocos consecutivos; picos são limitados na saída.
        def callback(indata, outdata, frames, time_info, status):
            try:
                block = engine.process(indata)
                outdata[:] = np.clip(block * 0.2, -0.9, 0.9).astype(outdata.dtype)
            except Exception:
                outdata.fill(0)
                raise sd.CallbackAbort

        with sd.Stream(samplerate=args.rate, blocksize=args.blocksize,
                       channels=args.channels, dtype="float32",
                       device=(args.input_device, args.output_device),
                       callback=callback):
            print("Audio ativo: use fones e volume baixo. Ctrl+C interrompe.")
            sd.sleep(round(args.seconds * 1000))
    except (ValueError, sd.PortAudioError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
