from pathlib import Path
from io import BytesIO

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from signal_lab.audio import Audio, wav_bytes

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_demo_interface_and_presentation_show_real_measurements():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Visão geral", "Análise de sinais", "Equalização", "Apresentação"]
    assert len(app.get("download_button")) == 3
    result = app.session_state["result"]
    assert result.error_after_db < result.error_before_db
    app.toggle(key="presentation_mode").set_value(True).run()
    app.radio(key="presentation_slide").set_value("5 · Experimento").run()
    assert not app.exception
    assert any("Experimento" in title.value for title in app.title)
    assert any(metric.label == "Erro depois" and metric.value == f"{result.error_after_db:.3f} dB" for metric in app.metric)
    app.radio(key="presentation_slide").set_value("3 · Análise").run()
    assert not app.exception
    assert any(metric.label == "FFT efetiva" for metric in app.metric)


def test_controls_reprocess_and_missing_upload_has_clear_error():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    app.slider(key="strength_Demonstração pronta").set_value(0)
    app.button[0].click().run()
    assert not app.exception
    result = app.session_state["result"]
    assert result.settings.strength == 0
    np.testing.assert_array_equal(result.original.samples, result.processed.samples)
    app.radio(key="audio_source").set_value("Enviar áudio").run()
    app.button[0].click().run()
    assert not app.exception
    assert any("Envie um arquivo" in error.value for error in app.error)


def microphone_wav(seed=42):
    # Simula o WAV entregue pelo navegador, sem acessar o microfone físico.
    samples = np.random.default_rng(seed).normal(0, 0.05, 16_000)
    recording = BytesIO(wav_bytes(Audio(samples, 16_000)))
    recording.name = "audio.wav"
    return recording


def test_microphone_without_recording_keeps_last_result_and_explains_error(monkeypatch):
    monkeypatch.setattr("streamlit.audio_input", lambda *args, **kwargs: None)
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    previous = app.session_state["result"]
    app.radio(key="audio_source").set_value("Gravar áudio").run()
    assert not app.error
    app.button[0].click().run()
    assert not app.exception
    assert any("Grave e encerre" in error.value for error in app.error)
    assert app.session_state["result"] is previous


def test_microphone_recording_equalizes_exports_and_detects_new_capture(monkeypatch):
    recording = microphone_wav()
    monkeypatch.setattr("streamlit.audio_input", lambda *args, **kwargs: recording)
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    app.radio(key="audio_source").set_value("Gravar áudio").run()
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    result = app.session_state["result"]
    assert result.original.name == "gravacao_microfone.wav"
    assert result.settings.target == "gentle"
    assert result.original.sample_rate == 16_000
    assert result.original.samples.shape == result.processed.samples.shape
    assert result.error_after_db <= result.error_before_db + 1e-8
    assert len(app.get("download_button")) == 4
    assert any(button.proto.label == "↓ Gravação original · WAV" for button in app.get("download_button"))
    previous_signature = app.session_state["signature"]
    recording = microphone_wav(seed=43)
    app.run()
    assert app.session_state["result"] is result
    assert any("última análise concluída" in info.value for info in app.info)
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["signature"] != previous_signature
    assert not np.array_equal(app.session_state["result"].original.samples, result.original.samples)


@pytest.mark.parametrize("payload", [b"", b"nao e um WAV"])
def test_invalid_microphone_recording_is_reported_without_crashing(monkeypatch, payload):
    monkeypatch.setattr("streamlit.audio_input", lambda *args, **kwargs: BytesIO(payload))
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    app.radio(key="audio_source").set_value("Gravar áudio").run()
    app.button[0].click().run()
    assert not app.exception
    assert any("Não foi possível ler" in error.value for error in app.error)


def test_microphone_reference_requires_and_uses_uploaded_reference(monkeypatch):
    recording = microphone_wav()
    reference = None
    monkeypatch.setattr("streamlit.audio_input", lambda *args, **kwargs: recording)
    monkeypatch.setattr("streamlit.file_uploader", lambda *args, **kwargs: reference)
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    app.radio(key="audio_source").set_value("Gravar áudio").run()
    app.selectbox(key="target_Gravar áudio").set_value("reference").run()
    app.button[0].click().run()
    assert not app.exception
    assert any("Envie o arquivo de referência" in error.value for error in app.error)
    reference = microphone_wav(seed=43)
    app.run()
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    result = app.session_state["result"]
    assert result.settings.target == "reference"
    assert result.reference_name == reference.name
