"""Regressão visual: nitidez e paletas por modo nos gráficos do processamento."""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from signal_lab.audio import Audio
from signal_lab.charts import (
    MODE_TITLES, PALETTES, band_figure, gains_figure,
    palette, psd_figure, response_figure, waveform_figure,
)
from signal_lab.dsp import Settings, equalize


@pytest.fixture
def sample_audio():
    rate = 16_000
    t = np.arange(rate * 2) / rate
    rng = np.random.default_rng(1234)
    samples = (0.18 * np.sin(2 * np.pi * 180 * t)
               + 0.10 * np.sin(2 * np.pi * 1000 * t)
               + rng.normal(0, 0.01, len(t)))
    return Audio(samples, rate, "visual.wav")


def test_palettes_have_distinct_accessible_series_colors():
    assert set(PALETTES) == {"gentle", "flat", "reference", "voice"}
    pairs = [(colors["before"], colors["after"]) for colors in PALETTES.values()]
    assert len(pairs) == len(set(pairs))
    assert len({color for pair in pairs for color in pair}) == 8
    for colors in PALETTES.values():
        assert colors["before"] != colors["after"]
        assert colors["target"] not in (colors["before"], colors["after"])


@pytest.mark.parametrize("target", ["gentle", "flat", "reference", "voice"])
def test_band_figures_use_mode_palette_and_separate_markers(sample_audio, target):
    reference = sample_audio if target == "reference" else None
    result = equalize(sample_audio, Settings(target=target), reference)
    fig = band_figure(result)
    try:
        ax = fig.axes[0]
        colors = palette(result)
        assert fig.dpi >= 150
        assert ax.get_title(loc="left") == MODE_TITLES[target]
        assert len(ax.lines) == (2 if target == "voice" else 3)
        assert ax.lines[0].get_color() == colors["before"]
        assert ax.lines[-1].get_color() == colors["after"]
        assert ax.lines[0].get_marker() != ax.lines[-1].get_marker()
        if target != "voice":
            assert ax.lines[1].get_color() == colors["target"]
        # Desenhar integralmente para detectar problemas no backend de gráficos.
        fig.canvas.draw()
    finally:
        plt.close(fig)


@pytest.mark.parametrize("target", ["gentle", "flat", "reference", "voice"])
def test_all_comparison_charts_follow_selected_mode(sample_audio, target):
    result = equalize(sample_audio, Settings(target=target),
                      sample_audio if target == "reference" else None)
    colors = palette(result)
    charts = [
        (psd_figure(result), colors["before"], colors["after"]),
        (response_figure(result), colors["after"], None),
        (waveform_figure(result), None, None),
        (gains_figure(result), None, None),
    ]
    try:
        psd = charts[0][0]
        assert psd.axes[0].lines[0].get_color() == colors["before"]
        assert psd.axes[0].lines[1].get_color() == colors["after"]
        response = charts[1][0]
        assert response.axes[0].lines[0].get_color() == colors["after"]
        for fig, _, _ in charts:
            assert fig.dpi >= 150
            fig.canvas.draw()
    finally:
        for fig, _, _ in charts:
            plt.close(fig)
