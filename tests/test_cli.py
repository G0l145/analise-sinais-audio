import json

from signal_lab.audio import read_audio, wav_bytes
from signal_lab.cli import main


def test_cli_exports_reproducible_demo_and_refuses_overwrite(tmp_path):
    out = tmp_path / "demo"
    assert main(["demo", "--out", str(out)]) == 0
    report = json.loads((out / "relatorio.json").read_bytes())
    assert report["relative_shape_rmse_reduction_percent"] > 60
    assert (out / "bandas.png").stat().st_size > 1000
    assert (out / "espectro.png").stat().st_size > 1000
    assert (out / "bandas.csv").read_text(encoding="utf-8-sig").startswith("Centro (Hz);")
    original = (out / "audio_equalizado.wav").read_bytes()
    assert main(["demo", "--out", str(out)]) == 2
    assert (out / "audio_equalizado.wav").read_bytes() == original


def test_cli_leaves_source_unchanged(tmp_path, tone):
    input_file = tmp_path / "entrada.wav"
    source = wav_bytes(tone)
    input_file.write_bytes(source)
    out = tmp_path / "saida"
    assert main(["equalize", str(input_file), "--out", str(out)]) == 0
    assert input_file.read_bytes() == source
    assert read_audio(out / "audio_equalizado.wav").samples.shape == tone.samples.shape
