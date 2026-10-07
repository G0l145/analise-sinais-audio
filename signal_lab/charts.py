"""Figuras com unidades, mesma escala e envelope que preserva os picos."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analysis import CENTERS, EPS, centered
from .dsp import Result, frequency_response

BEFORE = "#638d91"
AFTER = "#13846c"
TARGET = "#be7e39"
INK = "#233b38"
LABELS = ["31,5", "63", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]


def figure(rows=1, height=3.7):
    fig, axes = plt.subplots(rows, 1, figsize=(10.8, height), squeeze=False, layout="constrained")
    fig.patch.set_facecolor("#f6f8f7")
    for ax in axes.flat:
        ax.set_facecolor("#f6f8f7")
        ax.grid(True, color="#dde5df", linewidth=0.7, alpha=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#c6d2cb")
        ax.tick_params(colors=INK, labelsize=9)
        ax.xaxis.label.set_color(INK)
        ax.yaxis.label.set_color(INK)
    return fig, axes[:, 0]


def band_figure(result: Result):
    fig, (ax,) = figure()
    x = np.arange(10)
    ax.plot(x, centered(result.before.band_db, result.mask), "o-", color=BEFORE, label="Antes", linewidth=2)
    ax.plot(x, result.target_db, "--", color=TARGET, label="Alvo", linewidth=1.8)
    ax.plot(x, centered(result.after.band_db, result.mask), "o-", color=AFTER, label="Depois", linewidth=2)
    ax.set_xticks(x, LABELS)
    ax.set_xlabel("Frequência central da banda (Hz)")
    ax.set_ylabel("Potência relativa à média das bandas (dB)")
    ax.legend(frameon=False, ncols=3)
    return fig


def psd_figure(result: Result):
    fig, (ax,) = figure()
    for analysis, color, label in [(result.before, BEFORE, "Antes"), (result.after, AFTER, "Depois")]:
        mask = analysis.frequencies >= 20
        ax.semilogx(analysis.frequencies[mask], 10 * np.log10(np.maximum(analysis.psd[mask], EPS)),
                    color=color, label=label, linewidth=1.1, alpha=0.9)
    ax.set_xlim(20, result.original.sample_rate / 2)
    ax.set_xlabel("Frequência (Hz, escala logarítmica)")
    ax.set_ylabel("PSD (dB relativos a FS²/Hz)")
    ax.legend(frameon=False, ncols=2)
    return fig


def waveform_figure(result: Result):
    fig, axes = figure(result.original.channels, height=2.3 * result.original.channels + 0.8)
    n = len(result.original.samples)
    step = max(1, int(np.ceil(n / 1800)))
    indices = np.arange(0, n, step)
    times = indices / result.original.sample_rate
    for channel, ax in enumerate(axes):
        for audio, color, label in [(result.original, BEFORE, "Antes"), (result.processed, AFTER, "Depois")]:
            values = audio.samples[:, channel]
            low = np.minimum.reduceat(values, indices)
            high = np.maximum.reduceat(values, indices)
            ax.fill_between(times, low, high, color=color, alpha=0.38, label=label)
        ax.set_ylabel("Amplitude (FS)")
        ax.set_title("Mono" if len(axes) == 1 else ["Canal esquerdo", "Canal direito"][channel], loc="left", color=INK, fontsize=10)
        ax.set_xlim(0, result.original.duration)
        if channel == 0:
            ax.legend(frameon=False, ncols=2)
    limit = max(float(np.max(np.abs(result.original.samples))), float(np.max(np.abs(result.processed.samples))), 0.01) * 1.05
    for ax in axes:
        ax.set_ylim(-limit, limit)
    axes[-1].set_xlabel("Tempo (s)")
    return fig


def _edges(centers, single_width):
    if len(centers) == 1:
        return np.array([centers[0] - single_width / 2, centers[0] + single_width / 2])
    middle = (centers[:-1] + centers[1:]) / 2
    return np.r_[centers[0] - (middle[0] - centers[0]), middle, centers[-1] + (centers[-1] - middle[-1])]


def spectrogram_figure(result: Result):
    fig, axes = figure(2, height=6.3)
    top = max(float(np.max(result.before.spectrogram_db)), float(np.max(result.after.spectrogram_db)))
    bottom = top - 80
    mesh = None
    for analysis, ax, label in [(result.before, axes[0], "Antes"), (result.after, axes[1], "Depois")]:
        bins = np.flatnonzero(analysis.frequencies >= 20)
        if len(bins) > 512:
            # Apenas a figura é amostrada; a STFT e as potências permanecem integrais.
            bins = np.unique(np.round(np.geomspace(bins[0], bins[-1], 512)).astype(int))
        frequencies = analysis.frequencies[bins]
        if len(frequencies) < 2:
            ax.text(0.5, 0.5, "Áudio muito curto para um espectrograma útil", ha="center", transform=ax.transAxes)
            continue
        f_edges = _edges(frequencies, result.original.sample_rate / analysis.n_fft)
        t_edges = _edges(analysis.frame_times, analysis.hop / result.original.sample_rate)
        mesh = ax.pcolormesh(t_edges, f_edges, analysis.spectrogram_db[bins],
                             cmap="viridis", vmin=bottom, vmax=top, shading="flat", rasterized=True)
        ax.set_yscale("log")
        ax.set_ylim(max(20, f_edges[0]), result.original.sample_rate / 2)
        ax.set_xlim(0, result.original.duration)
        ax.set_ylabel("Frequência (Hz)")
        ax.set_title(label, loc="left", color=INK, fontsize=11)
        ax.grid(False)
    axes[-1].set_xlabel("Tempo (s)")
    if mesh is not None:
        fig.colorbar(mesh, ax=list(axes), label="PSD (dB relativos a FS²/Hz)", pad=0.02, shrink=0.88)
    return fig


def gains_figure(result: Result):
    fig, (ax,) = figure()
    colors = [AFTER if g >= 0 else BEFORE for g in result.gains_db]
    ax.bar(np.arange(10), result.gains_db, color=colors, width=0.63)
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_xticks(np.arange(10), LABELS)
    ax.set_ylim(-6.8, 6.8)
    ax.set_xlabel("Frequência central do filtro (Hz)")
    ax.set_ylabel("Ganho por filtro (dB)")
    for i, gain in enumerate(result.gains_db):
        ax.text(i, gain + (0.22 if gain >= 0 else -0.22), f"{gain:+.1f}", ha="center",
                va="bottom" if gain >= 0 else "top", color=INK, fontsize=8)
    return fig


def response_figure(result: Result):
    fig, (ax,) = figure()
    frequencies, gain = frequency_response(result)
    mask = frequencies >= 20
    ax.semilogx(frequencies[mask], gain[mask], color=AFTER, linewidth=2, label="Cascata de filtros EQ")
    if result.attenuation_db < -1e-8:
        ax.semilogx(frequencies[mask], gain[mask] + result.attenuation_db, "--", color=TARGET,
                    label="EQ + atenuação global de pico")
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_xlim(20, result.original.sample_rate / 2)
    ax.set_xlabel("Frequência (Hz, escala logarítmica)")
    ax.set_ylabel("Resposta em magnitude (dB)")
    ax.legend(frameon=False)
    return fig
