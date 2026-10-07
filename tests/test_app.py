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
