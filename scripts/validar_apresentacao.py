"""Validação não destrutiva do projeto antes da apresentação acadêmica.

Uso: python scripts/validar_apresentacao.py
Os resultados temporários são apagados ao final; nenhum arquivo do usuário é modificado.
"""

from importlib.util import find_spec
import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIAS = (
    "numpy", "scipy", "soundfile", "matplotlib",
    "pyloudnorm", "streamlit", "pandas", "pytest",
)
ARQUIVOS = (
    "audio_equalizado.wav",
    "audio_original_demo.wav",
    "referencia_demo.wav",
    "relatorio.json",
    "bandas.csv",
    "bandas.png",
    "espectro.png",
)


def executar(*args: str) -> bool:
    print("\n> " + " ".join(args), flush=True)
    resultado = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
    return resultado.returncode == 0


def main() -> int:
    print("SINAL | Verificação antes da apresentação", flush=True)
    faltando = [modulo for modulo in DEPENDENCIAS if find_spec(modulo) is None]
    if faltando:
        print("FALHA: dependências ausentes: " + ", ".join(faltando))
        print("Instale com: python -m pip install -r requirements-dev.txt")
        return 2

    print("[1/3] Executando os testes automatizados...")
    if not executar("-m", "pytest", "-q"):
        print("FALHA: os testes não foram aprovados.")
        return 1

    print("[2/3] Gerando uma demonstração temporária...")
    with TemporaryDirectory(prefix="sinal-apresentacao-") as diretorio:
        destino = Path(diretorio) / "demo"
        if not executar("-m", "signal_lab.cli", "demo", "--out", str(destino)):
            print("FALHA: a demonstração não foi gerada.")
            return 1

        print("[3/3] Conferindo arquivos e medições...")
        ausentes = [nome for nome in ARQUIVOS if not (destino / nome).is_file()
                    or (destino / nome).stat().st_size == 0]
        if ausentes:
            print("FALHA: arquivos ausentes ou vazios: " + ", ".join(ausentes))
            return 1

        with (destino / "relatorio.json").open(encoding="utf-8") as arquivo:
            relatorio = json.load(arquivo)
        antes = relatorio["relative_shape_rmse_before_db"]
        depois = relatorio["relative_shape_rmse_after_db"]
        reducao = relatorio["relative_shape_rmse_reduction_percent"]
        audio = relatorio["audio"]
        valido = (
            all(isinstance(v, (int, float)) and math.isfinite(v)
                for v in (antes, depois, reducao))
            and antes > 0
            and 0 <= depois < antes
            and reducao > 0
            and audio["channels"] in (1, 2)
            and audio["samples_per_channel"] > 0
            and len(relatorio["bands"]) == 10
        )
        if not valido:
            print("FALHA: o relatório não comprovou a correção esperada.")
            return 1

        print(f"Erro relativo: {antes:.3f} -> {depois:.3f} dB")
        print(f"Redução medida: {reducao:.1f}%")
        print("Arquivos de áudio, gráficos e relatórios: OK")

    print("\nAPROVADO: os testes e a demonstração estão prontos para o ensaio.")
    print("Para abrir: python -m streamlit run app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
