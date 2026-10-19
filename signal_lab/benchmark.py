"""Avaliação em lote, usando somente arquivos de áudio fornecidos pelo usuário.

Exemplo:
 python -m signal_lab.benchmark audios-pessoais --out resultados/avaliacao.csv
"""
import argparse
import csv
from pathlib import Path
import sys

from .audio import read_audio
from .dsp import Settings, equalize
from .quality import compare_indicators

EXTENSIONS = {".wav", ".flac", ".mp3"}


def evaluate(directory: Path, out: Path, target: str = "gentle") -> tuple[int, int]:
    if not directory.is_dir():
        raise ValueError("Diretório de áudios não encontrado.")
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not files:
        raise ValueError("Nenhum áudio WAV, FLAC ou MP3 encontrado.")
    if out.resolve() in (p.resolve() for p in files) or out.exists():
        raise ValueError("O relatório já existe. Escolha outro destino; arquivos existentes não serão substituídos.")
    if target not in ("flat", "gentle"):
        raise ValueError("Benchmark em lote aceita flat ou gentle (referência exige par específico).")
    rows = []
    passed = 0
    for path in files:
        row = {"file": path.name, "status": "ok", "error": "",
               "before_rmse_db": "", "after_rmse_db": "", "improvement_percent": "",
               "centroid_before_hz": "", "centroid_after_hz": "",
               "crest_before_db": "", "crest_after_db": ""}
        try:
            result = equalize(read_audio(path), Settings(target=target))
            measures = compare_indicators(result.before, result.after)
            a, b = result.error_before_db, result.error_after_db
            row["before_rmse_db"] = a if a is not None else ""
            row["after_rmse_db"] = b if b is not None else ""
            row["improvement_percent"] = (100 * (1 - b / a)
                                          if a is not None and b is not None and a > 1e-9 else "")
            for suffix, position in (("before", "before"), ("after", "after")):
                row[f"centroid_{suffix}_hz"] = measures[position]["spectral_centroid_hz"]
                row[f"crest_{suffix}_db"] = measures[position]["crest_factor_db"]
            passed += 1
        except (OSError, ValueError, RuntimeError) as exc:
            row["status"] = "error"
            row["error"] = str(exc)
        rows.append(row)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return passed, len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Avaliação em lote de gravações autorizadas")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target", choices=("flat", "gentle"), default="gentle")
    args = parser.parse_args(argv)
    try:
        success, count = evaluate(args.directory, args.out, args.target)
    except (ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    print(f"Avaliados: {count}; concluídos: {success}; com erro: {count-success}. Relatório: {args.out}")
    return 0 if success == count else 1


if __name__ == "__main__":
    raise SystemExit(main())
