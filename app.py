"""Interface acadêmica: executar com python -m streamlit run app.py."""

import hashlib
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from signal_lab.audio import matched_pair, read_audio, safe_preview, wav_bytes
from signal_lab.charts import band_figure, gains_figure, psd_figure, response_figure, spectrogram_figure, waveform_figure
from signal_lab.demo import demo_pair
from signal_lab.dsp import Settings, equalize
from signal_lab.presentation import render_presentation
from signal_lab.report import TARGET_NAMES, band_table, csv_bytes, improvement_percent, json_bytes, make_report

st.set_page_config(page_title="Sinal · Análise e equalização de áudio", page_icon="🎛️", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1220px; padding-top: 2rem; padding-bottom: 2rem;}
.hero {background: linear-gradient(115deg,#153c34,#24574b); border-radius:22px; padding:32px 38px; margin-bottom:24px; color:#f7faf5;}
.hero .eyebrow {font-size:12px; letter-spacing:2.6px; font-weight:700; color:#b7d6c2;}
.hero h1 {color:#fff; font-size:clamp(28px,3.2vw,42px); line-height:1.12; letter-spacing:-1.3px; margin:13px 0; font-weight:650;}
.hero p {color:#d0e1d7; font-size:16px; margin-bottom:0; max-width:760px;}
div[data-testid="stMetric"] {background:#eef3ef; border:1px solid #dfe7df; border-radius:14px; padding:15px 18px;}
div[data-testid="stMetricValue"] {font-size:26px;}
button[data-baseweb="tab"] {font-size:15px; padding:14px 18px;}
h2 {letter-spacing:-.4px;}
@media(max-width:640px) {.hero{padding:24px;} .block-container{padding-top:1rem;}}
</style>
<div class="hero">
  <div class="eyebrow">SINAL / LABORATÓRIO DE ÁUDIO</div>
  <h1>Entenda o som.<br>Compare a transformação.</h1>
  <p>Análise espectral e equalização automática por dez bandas, com gráficos, escuta comparativa e critérios verificáveis.</p>
</div>
""", unsafe_allow_html=True)


def show_figure(fig):
    st.pyplot(fig)
    plt.close(fig)


def formatted(value, unit="", precision=2):
    return "—" if value is None else f"{value:.{precision}f}{unit}"


def upload_hash(upload):
    return None if upload is None else hashlib.sha256(upload.getvalue()).hexdigest()


with st.sidebar:
    st.title("🎛️ Sinal")
    st.caption("ANÁLISE DE SINAIS · PROJETO ACADÊMICO")
    source = st.radio("Fonte do áudio", ["Demonstração pronta", "Enviar áudio"], key="audio_source")
    uploaded = None
    uploaded_reference = None
    if source == "Enviar áudio":
        uploaded = st.file_uploader("Arquivo de entrada", type=["wav", "flac", "mp3"], key="input_upload")
        st.caption("Até 50 MB e 5 minutos; mono/estéreo. A taxa deve estar entre 8 e 96 kHz; limite adicional de 14,4 milhões de amostras por canal.")
    else:
        st.caption("Trecho sintético original de 12 segundos, com graves realçados e referência conhecida. Funciona sem enviar arquivos.")
    modes = ["reference", "gentle", "flat"] if source == "Demonstração pronta" else ["gentle", "flat", "reference"]
    target = st.selectbox("Curva-alvo", modes, format_func=lambda x: {"reference": "Áudio de referência", "gentle": "Curva suave · -1 dB/oitava", "flat": "Mesma potência por banda"}[x], key=f"target_{source}")
    if source == "Enviar áudio" and target == "reference":
        uploaded_reference = st.file_uploader("Arquivo de referência", type=["wav", "flac", "mp3"], key="reference_upload")
    with st.form("equalization_controls"):
        strength = st.slider("Intensidade da correção", 0.0, 1.0, 0.85 if source == "Demonstração pronta" else 0.65, 0.05, key=f"strength_{source}")
        with st.expander("Parâmetros dos filtros"):
            max_gain = st.slider("Limite por filtro (±dB)", 0.0, 6.0, 6.0, 0.5)
            q = st.slider("Fator de qualidade Q", 0.2, 5.0, 1.4, 0.1)
            ceiling = st.slider("Teto de pico de amostras (dBFS)", -12.0, -0.5, -1.0, 0.5)
        submitted = st.form_submit_button("Analisar e equalizar", type="primary", use_container_width=True)
    rms_match = st.toggle("Igualar RMS na escuta A/B", value=True, key="rms_match")
    st.caption("A equalização modifica o equilíbrio espectral. A opção de RMS modifica somente as prévias de escuta.")
    st.divider()
    st.caption("Os arquivos enviados são processados no ambiente que executa o aplicativo. Não são enviados ao GitHub. A aplicação não grava esses arquivos em disco.")

settings = Settings(target=target, strength=strength, max_gain_db=max_gain, q=q, ceiling_dbfs=ceiling)
signature = (source, upload_hash(uploaded), upload_hash(uploaded_reference), settings)

if submitted or "result" not in st.session_state:
    try:
        with st.spinner("Medindo o espectro, aplicando os filtros e validando a saída…"):
            if source == "Demonstração pronta":
                audio, reference = demo_pair()
            else:
                if uploaded is None:
                    raise ValueError("Envie um arquivo de áudio antes de iniciar a análise.")
                audio = read_audio(uploaded.getvalue(), uploaded.name)
                reference = None
                if settings.target == "reference":
                    if uploaded_reference is None:
                        raise ValueError("Envie o arquivo de referência para usar esse modo.")
                    reference = read_audio(uploaded_reference.getvalue(), uploaded_reference.name)
            result = equalize(audio, settings, reference if settings.target == "reference" else None)
            st.session_state["result"] = result
            st.session_state["reference"] = reference
            st.session_state["signature"] = signature
    except (ValueError, OSError) as exc:
        # Nunca associar o resultado anterior a uma nova entrada que falhou.
        for key in ("result", "reference", "signature",
                    "_preview_cache_result", "_preview_cache_rms", "_preview_cache_audio"):
            st.session_state.pop(key, None)
        st.error(f"Não foi possível concluir a análise: {exc}")
        st.stop()

if "result" not in st.session_state:
    st.info("Selecione a demonstração ou envie um arquivo para iniciar.")
    st.stop()

result = st.session_state["result"]
reference = st.session_state.get("reference")
if signature != st.session_state["signature"]:
    st.warning("Os controles ou arquivos foram alterados. Clique em “Analisar e equalizar” para gerar um resultado correspondente. A análise anterior permanece guardada, mas não será exibida nem exportada.")
    st.stop()
st.caption(f"RESULTADO ATUAL · {result.original.name} · {result.original.duration:.2f} s · {result.original.sample_rate:,} Hz · {result.original.channels} canal(is)".replace(",", "."))

# Os botões de navegação e a apresentação causam novas execuções do script.
# Guardar as prévias na sessão evita recodificar WAV a cada interação;
# a troca do resultado ou da opção RMS invalida este cache.
if (st.session_state.get("_preview_cache_result") is not result
        or st.session_state.get("_preview_cache_rms") != rms_match):
    if rms_match:
        preview_before, preview_after = matched_pair(result.original, result.processed)
    else:
        preview_before, preview_after = safe_preview(result.original), safe_preview(result.processed)
    st.session_state["_preview_cache_audio"] = (
        wav_bytes(preview_before), wav_bytes(preview_after)
    )
    st.session_state["_preview_cache_result"] = result
    st.session_state["_preview_cache_rms"] = rms_match
before_audio, after_audio = st.session_state["_preview_cache_audio"]
presentation_mode = st.toggle("Modo de apresentação ao professor", key="presentation_mode")

if presentation_mode:
    render_presentation(result, before_audio, after_audio)
else:
    overview, analysis, correction, presentation = st.tabs(["Visão geral", "Análise de sinais", "Equalização", "Apresentação"])
    with overview:
        st.subheader("A mudança, medida em relação ao alvo")
        percentage = improvement_percent(result)
        a, b, c, d = st.columns(4)
        a.metric("Erro antes", formatted(result.error_before_db, " dB", 3))
        b.metric("Erro depois", formatted(result.error_after_db, " dB", 3))
        c.metric("Redução do erro", formatted(percentage, "%", 1))
        d.metric("Bandas usadas", f"{np.count_nonzero(result.mask)}/10")
        st.caption(TARGET_NAMES[result.settings.target] + (f" · {result.reference_name}" if result.reference_name else ""))
        show_figure(band_figure(result))
        st.caption("Potências das bandas centralizadas na respectiva média; o erro RMSE avalia a forma do espectro e não o volume global.")
        st.subheader("Escuta comparativa")
        a, b = st.columns(2)
        with a:
            st.markdown("**A · Antes da equalização**")
            st.audio(before_audio, format="audio/wav")
        with b:
            st.markdown("**B · Depois da equalização**")
            st.audio(after_audio, format="audio/wav")
        st.caption("Prévias com RMS igualado e proteção de pico." if rms_match else "Prévias com proteção de pico; os volumes podem ser diferentes.")
        if reference is not None and result.settings.target == "reference":
            with st.expander("Ouvir a referência usada no experimento"):
                st.audio(wav_bytes(safe_preview(reference)), format="audio/wav")
                st.caption("O player da referência não faz parte da comparação com RMS igualado.")
        st.subheader("Exportar o resultado")
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(result.original.name).stem)[:60] or "audio"
        a, b, c = st.columns(3)
        a.download_button("↓ Áudio equalizado · WAV", wav_bytes(result.processed), file_name=f"{stem}_equalizado.wav", mime="audio/wav", on_click="ignore", use_container_width=True)
        b.download_button("↓ Relatório completo · JSON", json_bytes(result), file_name=f"{stem}_relatorio.json", mime="application/json", on_click="ignore", use_container_width=True)
        c.download_button("↓ Medições por banda · CSV", csv_bytes(result), file_name=f"{stem}_bandas.csv", mime="text/csv", on_click="ignore", use_container_width=True)
        st.caption("WAV PCM de 24 bits com taxa, duração e canais preservados. A opção de RMS da escuta não altera o arquivo exportado.")
    with analysis:
        st.subheader("Domínio do tempo")
        show_figure(waveform_figure(result))
        st.caption("Envelopes mínimo/máximo preservam os picos de cada bloco visual. Mesma escala de amplitude nos dois sinais.")
        st.subheader("Domínio da frequência")
        show_figure(psd_figure(result))
        st.caption("Densidade espectral de potência unilateral média da STFT. O nível inclui a atenuação global aplicada à saída.")
        st.subheader("Como o espectro evolui no tempo")
        show_figure(spectrogram_figure(result))
        st.caption("Espectrogramas com a mesma escala de cor. A figura mostra até 360 janelas e 512 bins de frequência; todas as janelas completas e todos os bins entram no cálculo das potências.")
        st.subheader("Métricas do arquivo")
        stats_rows = [
            {"Métrica": "RMS (dBFS)", "Antes": result.before.stats["rms_dbfs"], "Depois": result.after.stats["rms_dbfs"]},
            {"Métrica": "Pico de amostras (dBFS)", "Antes": result.before.stats["sample_peak_dbfs"], "Depois": result.after.stats["sample_peak_dbfs"]},
            {"Métrica": "Loudness integrado (LUFS)", "Antes": result.before.stats["integrated_lufs"], "Depois": result.after.stats["integrated_lufs"]},
            {"Métrica": "Amostras em/acima de 0 dBFS", "Antes": result.before.stats["samples_at_or_above_full_scale"], "Depois": result.after.stats["samples_at_or_above_full_scale"]},
        ]
        st.dataframe(stats_rows, hide_index=True)
        st.caption("LUFS usa pyloudnorm e pode ser indisponível em silêncio ou trechos menores que 400 ms. A contagem em 0 dBFS é um indicador; não comprova sozinha distorção.")
    with correction:
        st.subheader("Ganhos realmente aplicados")
        show_figure(gains_figure(result))
        st.dataframe(band_table(result), hide_index=True)
        st.caption("Bandas excluídas recebem ganho zero e valores relativos indisponíveis. Cada filtro é limitado a ±6 dB; a soma das respostas pode exceder esse valor.")
        st.subheader("Resposta dos filtros em cascata")
        show_figure(response_figure(result))
        st.write(f"**Atenuação global para proteção de pico:** {result.attenuation_db:.2f} dB.")
        for note in result.notes:
            st.caption("• " + note)
        with st.expander("Parâmetros, coeficientes SOS e relatório auditável"):
            st.json(make_report(result))
    with presentation:
        render_presentation(result, before_audio, after_audio)

st.divider()
st.caption("Sinal · Laboratório acadêmico de análise de sinais. A aproximação ao alvo é verificável; a preferência sonora depende da escuta e do contexto musical.")
