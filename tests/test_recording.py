"""Contrato do WAV PCM16 recebido após uma captura; sem microfone físico."""

from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from signal_lab.audio import read_audio, wav_bytes
from signal_lab.dsp import Settings, equalize
from signal_lab.report import csv_bytes, json_bytes


@pytest.mark.parametrize("rate", [16_000, 44_100, 48_000])
@pytest.mark.parametrize("silent", [False, True])
def test_recorded_pcm16_can_be_equalized_and_exported(rate, silent):
    t = np.arange(rate) / rate
    samples = np.zeros(rate) if silent else (
        0.3 * np.sin(2 * np.pi * 125 * t)
        + 0.1 * np.sin(2 * np.pi * 500 * t)
        + 0.03 * np.sin(2 * np.pi * 2000 * t)
    )
    capture = BytesIO()
    sf.write(capture, samples, rate, format="WAV", subtype="PCM_16")
    payload = capture.getvalue()
    original = read_audio(payload, "gravacao_microfone.wav")
    saved = original.samples.copy()
    result = equalize(original, Settings(target="gentle"))
    output = wav_bytes(result.processed)
    restored = read_audio(output, "gravacao_microfone_equalizado.wav")

    np.testing.assert_array_equal(original.samples, saved)
    assert capture.getvalue() == payload
    assert restored.sample_rate == rate
    assert restored.samples.shape == original.samples.shape
    assert np.isfinite(restored.samples).all()
    assert np.max(np.abs(restored.samples)) <= 10 ** (-1 / 20) + 1.3e-7
    assert sf.info(BytesIO(output)).subtype == "PCM_24"
    assert json_bytes(result)
    assert csv_bytes(result)
    if silent:
        np.testing.assert_array_equal(restored.samples, 0)
    else:
        assert result.error_after_db <= result.error_before_db + 1e-8
