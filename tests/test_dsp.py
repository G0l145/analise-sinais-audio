import json

import numpy as np
import pytest
from scipy.signal import sosfreqz

from signal_lab.audio import Audio
from signal_lab.dsp import Settings, equalize, peaking_sos
from signal_lab.report import json_bytes


@pytest.mark.parametrize("gain", [-6.0, 0.0, 6.0])
def test_biquad_has_requested_gain_and_stable_poles(gain):
    sos = peaking_sos(1000, gain, 44100, q=1.4)
    _, response = sosfreqz(sos[None, :], worN=np.array([1000.]), fs=44100)
    assert 20 * np.log10(abs(response[0])) == pytest.approx(gain, abs=1e-8)
    assert np.all(np.abs(np.roots(sos[3:])) < 1)


def test_known_demo_moves_toward_reference(demo):
    original, reference = demo
    saved = original.samples.copy()
    result = equalize(original, Settings(target="reference", strength=0.85), reference)
    assert result.error_before_db > 3.0
    assert result.error_after_db < result.error_before_db * 0.35
    assert np.max(np.abs(result.gains_db)) <= 6
    assert np.max(np.abs(result.processed.samples)) <= 10 ** (-1 / 20) + 1e-12
    assert result.processed.samples.shape == original.samples.shape
    assert result.processed.sample_rate == original.sample_rate
    np.testing.assert_array_equal(original.samples, saved)


def test_strength_zero_preserves_unclipped_signal(demo):
    original, _ = demo
    result = equalize(original, Settings(strength=0))
    np.testing.assert_array_equal(result.processed.samples, original.samples)
    assert np.all(result.gains_db == 0)


def test_sample_peak_protection_uses_global_attenuation(tone):
    loud = Audio(tone.samples * 4, tone.sample_rate)
    result = equalize(loud, Settings(strength=0, ceiling_dbfs=-3))
    assert result.after.stats["sample_peak_dbfs"] == pytest.approx(-3, abs=1e-9)
    assert result.attenuation_db < 0
    assert result.after.stats["samples_at_or_above_full_scale"] == 0


def test_silence_is_finite_and_json_uses_null():
    result = equalize(Audio(np.zeros((44100, 2)), 44100))
    assert np.all(result.gains_db == 0)
    assert np.all(result.processed.samples == 0)
    assert result.error_after_db is None
    report = json.loads(json_bytes(result))
    assert report["metrics_after"]["integrated_lufs"] is None
    assert report["bands"][0]["target_relative_db"] is None
    assert report["analysis"]["tail_samples_not_analyzed"] >= 0


def test_failed_correction_falls_back_to_identity(monkeypatch, demo):
    import signal_lab.dsp as module
    original, reference = demo
    real_smooth = module.smooth_gains
    monkeypatch.setattr(module, "smooth_gains", lambda delta, mask: -real_smooth(delta, mask))
    result = equalize(original, Settings(target="reference", strength=0.85), reference)
    assert result.error_after_db <= result.error_before_db + 1e-8
    assert np.all(result.gains_db == 0)
    assert any("reduzida" in note for note in result.notes)


def test_reference_is_required_and_cannot_be_silent(tone):
    with pytest.raises(ValueError, match="referência"):
        equalize(tone, Settings(target="reference"))
    with pytest.raises(ValueError, match="energia"):
        equalize(tone, Settings(target="reference"), Audio(np.zeros(8192), 8192))


@pytest.mark.parametrize("kwargs", [
    {"strength": -1}, {"strength": 1.1}, {"max_gain_db": 7},
    {"q": 0}, {"ceiling_dbfs": 0}, {"strength": float("nan")}, {"target": "unknown"},
])
def test_invalid_settings_fail_explicitly(kwargs):
    with pytest.raises(ValueError):
        Settings(**kwargs)
