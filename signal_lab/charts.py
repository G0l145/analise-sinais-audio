"""Figuras com unidades, mesma escala e envelope que preserva os picos."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analysis import CENTERS, EPS, centered
from .dsp import Result, frequency_response

# Paletas distintas por modo: contraste também por símbolos e traçados.
PALETTES = {
    "gentle": {"before": "#1D4ED8", "after": "#EA580C", "target": "#475569"},
    "flat": {"before": "#6D28D9", "after": "#047857", "target": "#9A3412"},
    "reference": {"before": "#BE123C", "after": "#0369A1", "target": "#713F12"},
    "voice": {"before": "#BE185D", "after": "#0F766E", "target": "#475569"},
}
MODE_TITLES = {
    "gentle": "Curva suave · -1 dB/oitava",
    "flat": "Mesma potência por banda",
    "reference": "Áudio de referência",
    "voice": "Voz nítida · limpeza e realce",
}
INK = "#142439"


def palette(result: Result) -> dict:
    return PALETTES[result.settings.target]
LABELS = ["31,5", "63", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]


def figure(rows=1, height=4.5):
    # A resolução elevada melhora a leitura em telas de projeção e no zoom do navegador.
    fig, axes = plt.subplots(rows, 1, figsize=(11.6, height), dpi=165, squeeze=False, layout="constrained")
    fig.patch.set_facecolor("#FFFFFF")
    for ax in axes.flat:
        ax.set_facecolor("#FFFFFF")
        ax.grid(True, axis="y", color="#CBD5E1", linewidth=0.9, alpha=0.75)
        ax.grid(True, axis="x", color="#E2E8F0", linewidth=0.6, alpha=0.45)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#94A3B8")
        ax.tick_params(colors=INK, labelsize=10.5, width=0.8)
        ax.xaxis.label.set_color(INK)
        ax.yaxis.label.set_color(INK)
        ax.xaxis.label.set_fontsize(11.5)
        ax.yaxis.label.set_fontsize(11.5)
    return fig, axes[:, 0]


def band_figure(result: Result):
    fig, (ax,) = figure(height=5.0)
    colors = palette(result)
    x = np.arange(10)
    ax.plot(x, centered(result.before.band_db, result.mask), "-o", color=colors["before"],
            label="Antes", linewidth=2.8, markersize=7, markeredgecolor="white", markeredgewidth=1.3, zorder=3)
    if result.settings.target != "voice":
        ax.plot(x, result.target_db, "--", color=colors["target"],
                label="Alvo", linewidth=2.3, dashes=(5, 3), zorder=2)
    ax.plot(x, centered(result.after.band_db, result.mask), "-s", color=colors["after"],
            label="Depois", linewidth=2.8, markersize=7, markeredgecolor="white", markeredgewidth=1.3, zorder=4)
    ax.set_xticks(x, LABELS)
    ax.set_xlabel("Frequência central da banda (Hz)", labelpad=10)
    ax.set_ylabel("Potência relativa à média das bandas (dB)", labelpad=8)
    ax.set_title(MODE_TITLES[result.settings.target], loc="left", fontsize=14,
                 fontweight="bold", color=INK, pad=26)
    ax.legend(frameon=False, ncols=3, fontsize=11, loc="upper right", bbox_to_anchor=(1.0, 1.14))
    return fig


def psd_figure(result: Result):
    fig, (ax,) = figure()
    colors = palette(result)
    for analysis, color, label in [(result.before, colors["before"], "Antes"), (result.after, colors["after"], "Depois")]:
        mask = analysis.frequencies >= 20
        ax.semilogx(analysis.frequencies[mask], 10 * np.log10(np.maximum(analysis.psd[mask], EPS)),
                    color=color, label=label, linewidth=1.1, alpha=0.9)
    ax.set_xlim(20, result.original.sample_rate / 2)
    ax.set_xlabel("Frequência (Hz, escala logarítmica)")
    ax.set_ylabel("PSD (dB relativos a FS²/Hz)")
    ax.legend(frameon=False, ncols=2)
    return fig


def waveform_figure(result: Result):
    fig, axes = figure(result.original.channels, height=2.9 * result.original.channels + 1.1)
    colors = palette(result)
    n = len(result.original.samples)
    step = max(1, int(np.ceil(n / 1800)))
    indices = np.arange(0, n, step)
    times = indices / result.original.sample_rate
    for channel, ax in enumerate(axes):
        for audio, color, label in [(result.original, colors["before"], "Antes"), (result.processed, colors["after"], "Depois")]:
            values = audio.samples[:, channel]
            low = np.minimum.reduceat(values, indices)
            high = np.maximum.reduceat(values, indices)
            ax.fill_between(times, low, high, color=color, alpha=0.32, label=label)
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
        cmap = {"gentle": "viridis", "flat": "plasma", "reference": "cividis", "voice": "magma"}[result.settings.target]
        mesh = ax.pcolormesh(t_edges, f_edges, analysis.spectrogram_db[bins],
                             cmap=cmap, vmin=bottom, vmax=top, shading="flat", rasterized=True)
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
    mode_colors = palette(result)
    colors = [mode_colors["after"] if g >= 0 else mode_colors["before"] for g in result.gains_db]
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
    colors = palette(result)
    frequencies, gain = frequency_response(result)
    mask = frequencies >= 20
    ax.semilogx(frequencies[mask], gain[mask], color=colors["after"], linewidth=2.5, label=("Filtros lineares de voz" if result.settings.target == "voice" else "Cascata de filtros EQ"))
    if result.attenuation_db < -1e-8:
        ax.semilogx(frequencies[mask], gain[mask] + result.attenuation_db, "--", color=colors["target"],
                    label="EQ + atenuação global de pico")
    ax.axhline(0, color=INK, linewidth=0.7)
    ax.set_xlim(20, result.original.sample_rate / 2)
    ax.set_xlabel("Frequência (Hz, escala logarítmica)")
    ax.set_ylabel("Resposta em magnitude (dB)")
    ax.legend(frameon=False)
    return fig
