from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

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


def test_outdated_result_is_not_shown_or_downloadable():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert not app.exception
    assert len(app.get("download_button")) == 3

    # Mudar os parametros sem submeter nao pode atribuir a saida antiga
    # ao novo pedido; nem permitir exportar arquivos obsoletos.
    app.slider(key="strength_Demonstração pronta").set_value(0.35).run()
    assert not app.exception
    assert len(app.get("download_button")) == 0
    assert any("alterados" in warning.value for warning in app.warning)

    app.button[0].click().run()
    assert not app.exception
    assert len(app.get("download_button")) == 3
    assert app.session_state["result"].settings.strength == 0.35


def test_failed_new_request_does_not_keep_previous_result():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert "result" in app.session_state
    app.radio(key="audio_source").set_value("Enviar áudio").run()
    assert len(app.get("download_button")) == 0
    app.button[0].click().run()
    assert not app.exception
    assert any("Envie um arquivo" in error.value for error in app.error)
    assert "result" not in app.session_state
    assert len(app.get("download_button")) == 0


def test_preview_cache_reused_on_navigation():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert not app.exception
    previous = app.session_state["_preview_cache_audio"]
    result = app.session_state["result"]
    app.toggle(key="presentation_mode").set_value(True).run()
    assert not app.exception
    assert app.session_state["result"] is result
    assert app.session_state["_preview_cache_audio"] is previous
    app.toggle(key="rms_match").set_value(False).run()
    assert not app.exception
    assert app.session_state["_preview_cache_rms"] is False
