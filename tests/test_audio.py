from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from signal_lab.audio import Audio, matched_pair, read_audio, wav_bytes


def test_export_round_trip_preserves_shape_and_rate(tone):
    data = wav_bytes(tone)
    restored = read_audio(data, "exportado.wav")
    assert sf.info(BytesIO(data)).subtype == "PCM_24"
    assert restored.sample_rate == tone.sample_rate
    assert restored.samples.shape == tone.samples.shape
    np.testing.assert_allclose(restored.samples, tone.samples, atol=1.3e-7, rtol=0)


def test_rms_matching_only_attenuates_and_preserves_sources(tone):
    louder = Audio(tone.samples * 2, tone.sample_rate)
    saved_a, saved_b = tone.samples.copy(), louder.samples.copy()
    a, b = matched_pair(tone, louder)
    assert np.sqrt(np.mean(a.samples ** 2)) == pytest.approx(np.sqrt(np.mean(b.samples ** 2)), abs=1e-12)
    assert np.max(np.abs(a.samples)) <= 10 ** (-1 / 20) + 1e-12
    np.testing.assert_array_equal(tone.samples, saved_a)
    np.testing.assert_array_equal(louder.samples, saved_b)


@pytest.mark.parametrize("samples,rate", [
    (np.array([]), 44100),
    (np.zeros((10, 3)), 44100),
    (np.array([0, np.nan]), 44100),
    (np.array([0, np.inf]), 44100),
    (np.array([0, 1]), 4000),
    (np.array([0, 1]), 44100.0),
])
def test_rejects_invalid_audio(samples, rate):
    with pytest.raises(ValueError):
        Audio(samples, rate)


def test_rejects_corrupt_file_and_pcm_clipping():
    with pytest.raises(ValueError, match="Não foi possível"):
        read_audio(b"arquivo invalido")
    with pytest.raises(ValueError, match="proteção"):
        wav_bytes(Audio(np.array([1.0, -1.0]), 44100))


def test_limits_are_checked_before_decoding(monkeypatch, tone):
    import signal_lab.audio as module
    monkeypatch.setattr(module, "MAX_BYTES", 32)
    with pytest.raises(ValueError, match="50 MB"):
        read_audio(wav_bytes(tone))
    monkeypatch.setattr(module, "MAX_BYTES", 50 * 1024 * 1024)
    monkeypatch.setattr(module, "MAX_FRAMES", 100)
    with pytest.raises(ValueError, match="limite"):
        read_audio(wav_bytes(tone))
