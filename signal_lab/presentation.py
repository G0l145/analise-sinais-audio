"""Apresentação interativa apoiada no resultado real do processamento."""

import matplotlib.pyplot as plt
import streamlit as st

from .charts import band_figure, gains_figure
from .dsp import Result
from .report import improvement_percent

SLIDES = [
    "1 · Objetivo", "2 · Método", "3 · Análise", "4 · Correção", "5 · Experimento", "6 · Conclusão",
]


def render_presentation(result: Result, before_audio: bytes, after_audio: bytes):
    slide = st.radio("Etapas da apresentação", SLIDES, horizontal=True, key="presentation_slide")
    index = SLIDES.index(slide)
    st.caption(f"ETAPA {index + 1} DE 6 · ANÁLISE DE SINAIS")
    if index == 0:
        st.title("Equalização automática, com critério mensurável")
        st.markdown("O sistema mede a distribuição de potência do áudio e aplica filtros para aproximá-la de uma **curva-alvo explícita**.")
        a, b = st.columns(2)
        with a:
            st.subheader("Questão do projeto")
            st.markdown("Como ajustar automaticamente o equilíbrio entre graves, médios e agudos e demonstrar o efeito no domínio do tempo e da frequência?")
        with b:
            st.subheader("Hipótese verificável")
            st.markdown("Para um sinal com desequilíbrio conhecido, a correção deve reduzir o erro espectral relativo à referência, preservando duração e canais.")
        st.info("A redução do erro mede aproximação ao alvo escolhido. A preferência musical continua sendo uma avaliação de escuta.")
    elif index == 1:
        st.title("Do arquivo à comparação")
        stages = [
            ("01 · Entrada", "Arquivo mono/estéreo ou demonstração sintética. O original é preservado."),
            ("02 · Medição", "STFT com janela Hann e média da potência dos canais."),
            ("03 · Alvo", "Mesma potência por banda, curva suave ou referência conhecida."),
            ("04 · Filtros", "Dez biquads peaking IIR, suavização e limite de ±6 dB por filtro."),
            ("05 · Validação", "Remedição da saída; redução da correção se o erro aumentar."),
            ("06 · Evidência", "Gráficos, escuta A/B, métricas e exportação WAV/JSON/CSV."),
        ]
        for start in [0, 3]:
            columns = st.columns(3)
            for column, (title, body) in zip(columns, stages[start:start + 3]):
                with column, st.container(border=True):
                    st.subheader(title)
                    st.write(body)
        st.caption("Processamento em Python com NumPy/SciPy; interface em Streamlit. O cálculo é determinístico, sem modelo de IA.")
    elif index == 2:
        st.title("Medir o sinal em janelas")
        st.latex(r"X(m,k)=\sum_{n=0}^{N-1}x[n+mH]w[n]e^{-j2\pi kn/N}")
        st.latex(r"P_c(m,k)=\frac{d_k\,|X_c(m,k)|^2}{f_s\sum_n w[n]^2},\qquad E_i=\sum_{k\in B_i}\overline{P}(k)\,\Delta f")
        st.markdown("A média é calculada **em potência**, por janela e por canal. Isso evita cancelar um sinal estéreo com canais em oposição de fase.")
        c1, c2, c3 = st.columns(3)
        c1.metric("FFT efetiva", f"{result.before.n_fft:,}".replace(",", "."))
        c2.metric("Passo em frequência", f"{result.original.sample_rate / result.before.n_fft:.2f} Hz")
        c3.metric("Janelas completas", str(result.before.frames))
        st.caption("H = N/2; Hann periódica; dₖ = 2 nos bins internos e 1 em DC/Nyquist. Δf indica o passo entre bins, não a resolução efetiva da janela.")
        st.info("Bandas: 31,5; 63; 125; 250; 500; 1.000; 2.000; 4.000; 8.000; 16.000 Hz. Bandas sem energia relevante ou próximas de Nyquist são excluídas.")
    elif index == 3:
        st.title("Transformar a diferença em filtros")
        st.latex(r"\widetilde M_i=M_i-\langle M\rangle,\quad\widetilde T_i=T_i-\langle T\rangle")
        st.latex(r"G_i=\operatorname{clip}\!\left(\alpha\,\operatorname{suavizar}(\widetilde T_i-\widetilde M_i),-G_{max},G_{max}\right)")
        st.latex(r"H_i(z)=\frac{b_0+b_1z^{-1}+b_2z^{-2}}{1+a_1z^{-1}+a_2z^{-2}},\qquad H(z)=\prod_i H_i(z)")
        fig = gains_figure(result)
        st.pyplot(fig)
        plt.close(fig)
        st.caption(f"Intensidade α = {result.settings.strength:.2f}; Q = {result.settings.q:.2f}; limite por filtro = ±{result.settings.max_gain_db:.1f} dB. A resposta da cascata pode exceder o ganho de um filtro isolado.")
        st.markdown("A suavização usa pesos ¼, ½ e ¼ entre bandas vizinhas disponíveis. A saída é medida novamente; se necessário, testa-se metade da correção ou identidade. Uma atenuação global respeita o teto de pico de amostras.")
    elif index == 4:
        st.title("Experimento: comparar antes e depois")
        percent = improvement_percent(result)
        a, b, c = st.columns(3)
        a.metric("Erro antes", "—" if result.error_before_db is None else f"{result.error_before_db:.3f} dB")
        b.metric("Erro depois", "—" if result.error_after_db is None else f"{result.error_after_db:.3f} dB")
        c.metric("Redução do erro", "—" if percent is None else f"{percent:.1f}%")
        fig = band_figure(result)
        st.pyplot(fig)
        plt.close(fig)
        a, b = st.columns(2)
        with a:
            st.write("**A · Antes**")
            st.audio(before_audio, format="audio/wav")
        with b:
            st.write("**B · Depois**")
            st.audio(after_audio, format="audio/wav")
        st.latex(r"\mathrm{RMSE}=\sqrt{\frac{1}{|B|}\sum_{i\in B}(\widetilde M_i-\widetilde T_i)^2}")
        st.caption(f"Resultado atual: {result.original.name}. Referência: {result.reference_name or 'curva-alvo matemática'}. Os valores vêm do áudio processado nesta sessão.")
    else:
        st.title("Resultado, limites e evolução")
        a, b = st.columns(2)
        with a:
            st.subheader("O que foi demonstrado")
            st.markdown("- Análise no tempo e na frequência.\n- Correção automática por dez bandas.\n- Validação quantitativa em relação ao alvo.\n- Escuta comparativa e saída auditável.")
        with b:
            st.subheader("Limites do experimento")
            st.markdown("- Curva-alvo depende do objetivo musical.\n- EQ não restaura distorção preexistente.\n- Filtros IIR alteram a fase e têm transientes.\n- Pico de amostras não mede true peak.\n- Processamento de arquivo, sem tempo real.")
        st.markdown("**Próximas etapas possíveis:** medição de true peak, comparação por LUFS e calibração com respostas de equipamentos, cada uma com avaliação específica.")
        st.success("A evidência central é a mudança medida no espectro. Uma conclusão sobre qualidade sonora exige também avaliação auditiva.")
    with st.expander("Roteiro de fala e perguntas do professor"):
        st.markdown("**Roteiro de 5–7 minutos:** apresente o objetivo (40 s), o fluxo (40 s), a STFT (60 s), os ganhos e filtros (60 s), execute a comparação (90 s) e discuta os limites (40 s).")
        st.markdown("**Por que não deixar todo o espectro plano?** O alvo usa potência integrada por bandas aproximadamente logarítmicas. Uma PSD plana e a mesma potência por oitava são critérios diferentes.")
        st.markdown("**O sistema sempre melhora a música?** Ele busca reduzir o erro relativo ao alvo. Isso não garante preferência subjetiva ou recuperação de uma gravação distorcida.")
        st.markdown("**Por que igualar RMS na escuta?** Para reduzir a influência do volume na comparação. RMS igualado não significa percepção de loudness idêntica.")
