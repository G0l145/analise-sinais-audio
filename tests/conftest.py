import numpy as np
import pytest

from signal_lab.audio import Audio
from signal_lab.demo import demo_pair


@pytest.fixture(scope="session")
def demo():
    return demo_pair(duration=3.0)


@pytest.fixture
def tone():
    rate = 8192
    time = np.arange(rate) / rate
    return Audio(0.4 * np.sin(2 * np.pi * 1000 * time), rate, "tom.wav")
