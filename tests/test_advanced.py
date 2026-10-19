import numpy as np
import pytest
from scipy.signal import sosfilt

from signal_lab.advanced_filters import FilterSpec, design_filter, filter_response, process_filter
from signal_lab.streaming import StreamingEQ


@pytest.mark.parametrize("kind", ["lowpass", "highpass", "lowshelf", "highshelf"])
def test_filters_are_finite_and_stable(kind):
    sos = design_filter(FilterSpec(kind, 1000, 4.0), 44100)
    assert sos.shape[1] == 6
    assert np.all(np.isfinite(sos))
    assert all(np.all(np.abs(np.roots(section[3:])) < 1) for section in sos)
    freq, db = filter_response(FilterSpec(kind, 1000, 4.0), 44100)
    assert len(freq) == len(db)
    assert np.isfinite(db).all()


def test_shelves_have_expected_low_and_high_frequency_response():
    f, low = filter_response(FilterSpec("lowshelf", 1000, 6), 44100, 8192)
    assert low[np.argmin(abs(f - 40))] > 5.5
    assert abs(low[np.argmin(abs(f - 12000))]) < 0.5
    f, high = filter_response(FilterSpec("highshelf", 1000, -6), 44100, 8192)
    assert abs(high[np.argmin(abs(f - 40))]) < 0.5
    assert high[np.argmin(abs(f - 12000))] < -5.5


def test_filter_rejects_invalid_parameters():
    with pytest.raises(ValueError):
        design_filter(FilterSpec("lowpass", 30000), 44100)
    with pytest.raises(ValueError):
        design_filter(FilterSpec("lowshelf", 1000, float("nan")), 44100)


def test_stream_matches_contiguous_sosfilt_and_reset():
    rng = np.random.default_rng(11)
    samples = rng.normal(0, 0.1, (4097, 2))
    sos = design_filter(FilterSpec("highshelf", 3500, -3), 44100)
    expected = sosfilt(sos, samples, axis=0)
    engine = StreamingEQ(sos, 2)
    actual = np.vstack([engine.process(samples[i:i+257]) for i in range(0, len(samples), 257)])
    np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=1e-12)
    engine.reset()
    np.testing.assert_allclose(engine.process(samples[:80]), expected[:80], atol=1e-12)


def test_stream_rejects_invalid_shape_and_non_finite():
    engine = StreamingEQ(design_filter(FilterSpec(), 44100), 1)
    with pytest.raises(ValueError):
        engine.process(np.zeros(16))
    with pytest.raises(ValueError):
        engine.process(np.full((16, 1), np.nan))


def test_stream_rejects_a0_close_but_not_exact():
    sos = design_filter(FilterSpec(), 44100).copy()
    sos[0, 3] = 1.000001
    with pytest.raises(ValueError, match="exatamente"):
        StreamingEQ(sos, 1)
