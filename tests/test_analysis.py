import numpy as np
import pytest

from signal_lab.analysis import analyze
from signal_lab.audio import Audio


def test_stft_power_matches_known_sine(tone):
    result = analyze(tone)
    df = tone.sample_rate / result.n_fft
    assert np.sum(result.psd) * df == pytest.approx(0.4 ** 2 / 2, rel=1e-10)
    assert result.frequencies[np.argmax(result.psd)] == 1000
    assert result.band_power[5] == pytest.approx(0.4 ** 2 / 2, rel=1e-10)
    assert result.stats["rms_dbfs"] == pytest.approx(20 * np.log10(0.4 / np.sqrt(2)), abs=1e-8)


def test_antiphase_stereo_does_not_cancel(tone):
    stereo = Audio(np.column_stack([tone.samples[:, 0], -tone.samples[:, 0]]), tone.sample_rate)
    a, b = analyze(tone), analyze(stereo)
    np.testing.assert_allclose(a.psd, b.psd, rtol=1e-12, atol=1e-20)
    assert b.band_power[5] > 0.07


def test_late_frames_affect_measurement():
    rate = 8192
    t = np.arange(3 * rate) / rate
    signal = np.sin(2 * np.pi * 1000 * t) * 0.1
    signal[rate:] *= 3
    result = analyze(Audio(signal, rate), max_columns=1)
    first = analyze(Audio(signal[:rate], rate))
    assert result.frames == 5
    assert result.spectrogram_db.shape[1] == 1
    assert result.band_power[5] > first.band_power[5] * 5


def test_short_audio_has_safe_incomplete_metrics():
    result = analyze(Audio(np.array([0.1, -0.1]), 8000))
    assert result.n_fft == 2
    assert result.stats["integrated_lufs"] is None
    assert not result.usable.any()


def test_low_sample_rate_excludes_high_bands():
    rng = np.random.default_rng(5)
    result = analyze(Audio(rng.normal(0, 0.05, 8000), 8000))
    assert not result.usable[7:].any()
    assert result.usable[:7].all()
