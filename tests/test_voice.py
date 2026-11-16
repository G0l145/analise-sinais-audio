"""Regressão do modo de fala: sinal gravado, silêncio, níveis e preservação."""
from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from signal_lab.audio import Audio, read_audio, wav_bytes
from signal_lab.dsp import Settings, equalize
from signal_lab.report import json_bytes, make_report, voice_measurements


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
    assert rms(processed[pause]) < 0.8 * rms(original[pause])
    assert rms(processed[speech]) > 0.85 * rms(original[speech])


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


@pytest.mark.parametrize("rate", [16_000, 48_000])
def test_continuous_tone_not_mistaken_for_stationary_noise(rate):
    t = np.arange(2 * rate) / rate
    signal = 0.25 * np.sin(2 * np.pi * 180 * t)
    result = equalize(Audio(signal, rate), Settings(target="voice", strength=1.0))
    before = float(np.sqrt(np.mean(result.original.samples ** 2)))
    after = float(np.sqrt(np.mean(result.processed.samples ** 2)))
    assert after > 0.85 * before
    assert np.isfinite(result.processed.samples).all()


@pytest.mark.parametrize("rate", [8_000, 16_000, 48_000, 96_000])
def test_very_short_recording_stays_finite_and_exportable(rate):
    capture = Audio(np.array([0.25, 0.10]), rate)
    result = equalize(capture, Settings(target="voice"))
    assert result.processed.samples.shape == (2, 1)
    assert np.isfinite(result.processed.samples).all()
    assert wav_bytes(result.processed)


def test_voice_measurements_match_samples_and_report():
    result = equalize(fake_recording(), Settings(target="voice", strength=1.0))
    measured = voice_measurements(result)
    assert np.isfinite(measured["rms_before_dbfs"])
    assert np.isfinite(measured["rms_after_dbfs"])
    assert measured["rms_change_db"] == pytest.approx(
        measured["rms_after_dbfs"] - measured["rms_before_dbfs"]
    )
    assert measured["low_energy_selected_windows"] == 4
    assert measured["low_energy_total_windows"] == 20
    assert measured["low_energy_attenuation_db"] > 0
    assert measured["low_energy_attenuation_db"] == pytest.approx(
        measured["low_energy_before_dbfs"] - measured["low_energy_after_dbfs"]
    )
    assert make_report(result)["voice_measurements"] == measured


def test_voice_measurements_no_change_and_silence_without_fabricated_numbers():
    unchanged = equalize(fake_recording(), Settings(target="voice", strength=0))
    measured = voice_measurements(unchanged)
    assert measured["rms_change_db"] == pytest.approx(0)
    assert measured["low_energy_attenuation_db"] == pytest.approx(0)
    silent = equalize(Audio(np.zeros(16_000), 16_000), Settings(target="voice"))
    silent_metrics = voice_measurements(silent)
    assert silent_metrics["rms_before_dbfs"] is None
    assert silent_metrics["rms_change_db"] is None
    assert silent_metrics["low_energy_attenuation_db"] is None
    assert b'"voice_measurements"' in json_bytes(silent)


def test_voice_measurements_reject_musical_target():
    result = equalize(fake_recording(), Settings(target="flat"))
    with pytest.raises(ValueError, match="modo voice"):
        voice_measurements(result)
