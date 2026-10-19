"""Motor IIR por blocos com estado persistente, sem alocações de áudio globais.

Interface com hardware fica no exemplo sounddevice e exige ativação explícita.
"""
import numpy as np
from scipy.signal import sosfilt


class StreamingEQ:
    """Aplica a mesma cascata SOS a blocos sucessivos, preservando a memória IIR."""

    def __init__(self, sos: np.ndarray, channels: int = 1):
        rows = np.asarray(sos, dtype=np.float64)
        if rows.ndim != 2 or rows.shape[1] != 6 or not len(rows) or not np.isfinite(rows).all():
            raise ValueError("SOS inválido.")
        if channels not in (1, 2):
            raise ValueError("Aceita mono ou estéreo.")
        if not np.all(rows[:, 3] == 1.0):
            raise ValueError("Coeficientes SOS devem ter a0 = 1 exatamente.")
        self.sos = rows.copy()
        self.channels = channels
        self.zi = np.zeros((len(rows), 2, channels), dtype=np.float64)

    def process(self, block: np.ndarray) -> np.ndarray:
        x = np.asarray(block, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != self.channels or not np.isfinite(x).all():
            raise ValueError("Bloco inválido.")
        if not len(x):
            return x.copy()
        y, self.zi = sosfilt(self.sos, x, axis=0, zi=self.zi)
        return y

    def reset(self):
        self.zi.fill(0)
