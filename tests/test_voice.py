"""Regressão do modo de fala: sinal gravado, silêncio, níveis e preservação."""
from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from signal_lab.audio import Audio, read_audio, wav_bytes
from signal_lab.dsp import Settings, equalize
from signal_lab.report import json_bytes


def fake_recording(rate=16_000, duration=2.0, noise=0.02):
    """Fala sintética intermitente com ruído contínuo; não substitui voz real."""
    rng = np.random.default_rng(2026)
    t = np.arange(int(rate * duration)) / rate
    speech = (0.25 * np.sin(2 * np.pi * 180 * t)
              + 0.08 * np.sin(2 * np.pi * 1000 * t)
              + 0.04 * np.sin(2 * np.pi * 2000 * t))
    speech *= ((t > 0.5) & (t < 1.5))
    sample = speech + rng.normal(0, noise, len(t))
    payload = BytesIO()
    sf.write(payload, sample, rate, format="WAV", subtype="PCM_16")
    return read_audio(payload.getvalue(), "fala.wav")


@pytest.mark.parametrize("rate", [8_000, 16_000, 48_000])
def test_voice_recording_is_finite_and_exportable(rate):
    original = fake_recording(rate)
    saved = original.samples.copy()
    result = equalize(original, Settings(target="voice", strength=0.8))
    np.testing.assert_array_equal(original.samples, saved)
    assert result.settings.target == "voice"
    assert result.error_before_db is None
    assert result.error_after_db is None
    assert result.processed.sample_rate == rate
    assert result.processed.samples.shape == original.samples.shape
    assert np.isfinite(result.processed.samples).all()
    assert np.max(np.abs(result.processed.samples)) <= 10 ** (-1 / 20) + 1e-12
    assert np.isfinite(result.sos).all()
    assert np.isnan(result.target_db).all()
    restored = read_audio(wav_bytes(result.processed))
    assert restored.samples.shape == saved.shape
    assert b'"voice"' in json_bytes(result)


def test_voice_reduces_noise_in_pause_without_erasing_speech():
    result = equalize(fake_recording(), Settings(target="voice", strength=1.0))
    original = result.original.samples[:, 0]
    processed = result.processed.samples[:, 0]
    rate = result.original.sample_rate
    pause = slice(int(rate * 0.1), int(rate * 0.4))
    speech = slice(int(rate * 0.8), int(rate * 1.2))
    rms = lambda values: float(np.sqrt(np.mean(values ** 2)))
    assert rms(processed[pause]) < rms(original[pause])
    assert rms(processed[speech]) > 0.3 * rms(original[speech])


def test_zero_strength_is_identity_for_safe_signal():
    original = fake_recording()
    result = equalize(original, Settings(target="voice", strength=0.0))
    np.testing.assert_array_equal(result.processed.samples, original.samples)
    assert np.all(result.gains_db == 0)


def test_silent_recording_does_not_create_voice():
    original = Audio(np.zeros(16_000), 16_000, "silencio.wav")
    result = equalize(original, Settings(target="voice"))
    assert np.max(np.abs(result.processed.samples)) == 0
    assert result.after.stats["integrated_lufs"] is None
    assert json_bytes(result)


def test_voice_refuses_reference():
    audio = fake_recording()
    with pytest.raises(ValueError, match="não utiliza"):
        equalize(audio, Settings(target="voice"), audio)
