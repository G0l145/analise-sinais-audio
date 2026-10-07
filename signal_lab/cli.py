"""Execução reproduzível pelo terminal, sem sobrescrever arquivos existentes."""

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt

from .audio import read_audio, safe_preview, wav_bytes
from .charts import band_figure, psd_figure
from .demo import demo_pair
from .dsp import Settings, equalize
from .report import csv_bytes, json_bytes


def parser():
    root = argparse.ArgumentParser(description="Sinal: análise e equalização automática de áudio")
    sub = root.add_subparsers(dest="command")
    demo = sub.add_parser("demo", help="Executar o experimento com referência conhecida")
    demo.add_argument("--out", type=Path, default=Path("resultados/demo"))
    run = sub.add_parser("equalize", help="Processar um arquivo sem alterar a entrada")
    run.add_argument("input", type=Path)
    run.add_argument("--reference", type=Path)
    run.add_argument("--target", choices=["flat", "gentle", "reference"], default="gentle")
    run.add_argument("--strength", type=float, default=0.65)
    run.add_argument("--out", type=Path, default=Path("resultados/audio"))
    return root


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    if args.command is None:
        root.print_help()
        return 0
    try:
        if args.command == "demo":
            original, reference = demo_pair()
            settings = Settings(target="reference", strength=0.85)
        else:
            original = read_audio(args.input)
            reference = read_audio(args.reference) if args.reference is not None else None
            if reference is not None and args.target != "reference":
                raise ValueError("Use --target reference junto com --reference.")
            settings = Settings(target=args.target, strength=args.strength)
        names = ["audio_equalizado.wav", "relatorio.json", "bandas.csv", "bandas.png", "espectro.png"]
        if args.command == "demo":
            names += ["audio_original_demo.wav", "referencia_demo.wav"]
        collisions = [str(args.out / name) for name in names if (args.out / name).exists()]
        if collisions:
            raise ValueError("Arquivos já existem. Escolha outra pasta com --out: " + ", ".join(collisions))
        # O diretório só é criado após validar entrada, destino e processamento.
        result = equalize(original, settings, reference)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "audio_equalizado.wav").write_bytes(wav_bytes(result.processed))
        (args.out / "relatorio.json").write_bytes(json_bytes(result))
        (args.out / "bandas.csv").write_bytes(csv_bytes(result))
        for name, make in [("bandas.png", band_figure), ("espectro.png", psd_figure)]:
            fig = make(result)
            fig.savefig(args.out / name, dpi=150)
            plt.close(fig)
        if args.command == "demo":
            (args.out / "audio_original_demo.wav").write_bytes(wav_bytes(safe_preview(original)))
            (args.out / "referencia_demo.wav").write_bytes(wav_bytes(safe_preview(reference)))
        print(f"Resultado salvo em: {args.out.resolve()}")
        if result.error_before_db is not None:
            print(f"Erro espectral relativo: {result.error_before_db:.3f} → {result.error_after_db:.3f} dB")
        print(f"Pico da saída: {result.after.stats['sample_peak_dbfs']} dBFS")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
