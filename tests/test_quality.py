import numpy as np
import pytest

from signal_lab.audio import Audio, wav_bytes
from signal_lab.analysis import analyze
from signal_lab.quality import spectral_indicators, compare_indicators
from signal_lab.benchmark import evaluate


def test_spectral_indicators_for_tone_and_silence(tone):
    data = spectral_indicators(analyze(tone))
    assert data["spectral_centroid_hz"] == pytest.approx(1000, abs=1)
    assert data["spectral_rolloff_85_hz"] == pytest.approx(1000, abs=2)
    assert 0 <= data["spectral_flatness"] <= 1
    assert data["crest_factor_db"] is not None
    empty = spectral_indicators(analyze(Audio(np.zeros(8192), 8192)))
    assert empty["spectral_centroid_hz"] is None
    assert empty["crest_factor_db"] is None


def test_comparison_zero_for_unchanged_analysis(tone):
    a = analyze(tone)
    comparison = compare_indicators(a, a)
    assert comparison["difference"]["spectral_centroid_hz"] == pytest.approx(0)
    assert comparison["difference"]["crest_factor_db"] == pytest.approx(0)


def test_benchmark_writes_csv_and_refuses_overwrite(tmp_path, tone):
    source = tmp_path / "audios"
    source.mkdir()
    (source / "tom.wav").write_bytes(wav_bytes(tone))
    destination = tmp_path / "relatorios" / "analise.csv"
    passed, total = evaluate(source, destination)
    assert (passed, total) == (1, 1)
    assert "tom.wav" in destination.read_text(encoding="utf-8-sig")
    with pytest.raises(ValueError, match="já existe"):
        evaluate(source, destination)


def test_benchmark_reports_invalid_audio_individually(tmp_path):
    source = tmp_path / "audios"
    source.mkdir()
    (source / "invalido.wav").write_bytes(b"not audio")
    passed, total = evaluate(source, tmp_path / "analise.csv")
    assert (passed, total) == (0, 1)
