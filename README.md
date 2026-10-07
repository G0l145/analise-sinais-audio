# Sinal — análise e equalização automática de áudio

Projeto para a disciplina **Análise de Sinais**: recebe um arquivo de áudio, mede o espectro por STFT, calcula uma correção em dez bandas, aplica filtros digitais e compara o resultado com um alvo explícito.

Inclui uma **apresentação ao professor em seis etapas**, com fórmulas, gráficos e um experimento reproduzível. A demonstração inicial é gerada pelo próprio programa; não exige baixar músicas.

## Abrir no GitHub Codespaces

1. Neste repositório, abra **Code → Codespaces → Create codespace on main**.
2. Aguarde a criação do ambiente e a instalação automática das dependências.
3. No terminal, execute:

```bash
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

4. Abra a porta **8501** na aba **Ports**, por **Open in Browser**. Mantenha a visibilidade **Private**.
5. O experimento sintético será analisado automaticamente. Para mostrar ao professor, ative **Modo de apresentação ao professor** ou abra a aba **Apresentação**.

O Codespaces utiliza a infraestrutura e a cota da conta GitHub. Depois da demonstração, pare o Codespace em **Your codespaces → Stop codespace**.

## Executar no Windows

Instale Python 3.11 ou superior. No PowerShell, dentro da pasta do repositório:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abra o endereço indicado no terminal, normalmente `http://localhost:8501`. Use `Ctrl+C` para encerrar. Os comandos usam o Python do ambiente diretamente e dispensam alterar a política de execução do PowerShell.

## Executar em Linux/macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m streamlit run app.py
```

## O que a interface oferece

| Área | Recursos |
|---|---|
| Visão geral | Erro antes/depois, redução percentual, bandas usadas, curva-alvo e escuta A/B |
| Análise de sinais | Forma de onda, PSD média, espectrogramas na mesma escala, RMS, pico e LUFS |
| Equalização | Ganhos aplicados, tabela por banda, resposta da cascata e coeficientes SOS |
| Apresentação | Objetivo, método, STFT, filtros, experimento e conclusão, com roteiro de fala |
| Exportação | Áudio WAV PCM de 24 bits, relatório JSON e tabela CSV |

### Como usar seu áudio

Selecione **Enviar áudio**, escolha um WAV/FLAC/MP3 e a curva-alvo. O modo **Áudio de referência** exige também um arquivo de referência. Clique em **Analisar e equalizar**.

Os controles podem ser alterados sem substituir o resultado anterior. A interface informa quando é necessário executar uma nova análise. O aplicativo mantém o áudio da sessão em memória; não grava uploads em disco nem os envia ao repositório. No Codespaces, o processamento acontece no servidor remoto do Codespace.

**Limites:** até 50 MB; até 300 segundos; até 14,4 milhões de amostras por canal; um ou dois canais; taxa entre 8 e 96 kHz. Os limites se aplicam simultaneamente: em 96 kHz, a quantidade máxima de amostras restringe a duração a 150 segundos. A leitura de MP3 depende do suporte da versão de libsndfile instalada. WAV e FLAC são preferíveis para o experimento.

## Critério de equalização

Não existe um ajuste ideal para toda música. O sistema oferece três critérios:

- **Mesma potência por banda:** equilibra a potência integrada nas bandas de aproximadamente uma oitava. Isso é diferente de tornar a PSD plana.
- **Curva suave:** potência por banda com inclinação de −1 dB por oitava.
- **Áudio de referência:** aproxima a forma espectral relativa da entrada à forma medida em outra gravação.

As bandas têm centros em **31,5; 63; 125; 250; 500; 1.000; 2.000; 4.000; 8.000; 16.000 Hz**. Ganhos são suavizados e limitados a **±6 dB por filtro**. Como os filtros se sobrepõem, a resposta total pode exceder esse limite.

O erro é o **RMSE, em dB, das potências relativas das bandas usadas**. Subtrair a média dos níveis de cada espectro remove a diferença global de volume. A saída é medida novamente; uma correção que aumentar esse erro é reduzida, podendo retornar à identidade. Uma redução do erro demonstra aproximação ao alvo, sem comprovar preferência sonora.

**Escuta A/B:** a opção de RMS igualado atua somente nas prévias e reduz a influência do volume. RMS igualado não garante loudness percebido idêntico. O áudio exportado corresponde à saída do processamento, sem a normalização das prévias.

## Terminal e experimento reproduzível

Depois de instalar as dependências, execute:

```bash
python -m signal_lab.cli demo --out resultados/demo-01
python -m signal_lab.cli equalize minha_musica.wav --target gentle --out resultados/musica-01
python -m signal_lab.cli equalize minha_musica.wav --target reference --reference referencia.wav --out resultados/referencia-01
```

O comando `demo` exporta a entrada sintética, a referência, a saída, os gráficos e as medições. Escolha outra pasta para repetir: o terminal recusa sobrescrever os arquivos de resultados já existentes. O arquivo de entrada permanece intacto.

Opcionalmente, `python -m pip install -e .` instala o comando `sinal`, equivalente a `python -m signal_lab.cli`.

## Validar

```bash
python -m pytest -q
```

Os testes verificam potência STFT, canais em oposição de fase, resposta dos biquads, estabilidade, limites de ganho, proteção de pico, silêncio, entradas inválidas, redução do erro em um experimento conhecido, exportação e interface. O workflow do GitHub repete os testes em Python 3.11 e 3.12.

## Método e limites técnicos

- STFT com Hann periódica, FFT de até 8.192 pontos e sobreposição de 50%; média da PSD unilateral das janelas completas e dos canais. A cauda que não completa uma janela é descartada e sua quantidade aparece no JSON.
- O espectrograma exibido é amostrado em tempo e frequência para limitar memória. As medições usam todas as janelas completas e todos os bins.
- Filtros **peaking IIR biquad** em cascata SOS. O MVP utiliza peaking nas dez bandas, inclusive nos extremos; não implementa shelving.
- Atenuação global para limitar **pico de amostras**. Não é um limitador de true peak e não recupera clipping preexistente.
- LUFS integrado pelo pyloudnorm; pode ser indisponível em silêncio ou trechos menores que 400 ms. Não há normalização de loudness da saída.
- Processamento offline de arquivos. Não há captura de microfone, processamento em tempo real ou calibração de caixas/fones.

Veja [METODOLOGIA.md](docs/METODOLOGIA.md) e [APRESENTACAO.md](docs/APRESENTACAO.md) para a explicação dos cálculos e o roteiro da demonstração.

## Referências primárias

- [W3C — Audio EQ Cookbook / Robert Bristow-Johnson](https://www.w3.org/TR/audio-eq-cookbook/): coeficientes de biquads.
- [SciPy — sosfilt](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfilt.html): aplicação de filtros em seções de segunda ordem.
- [pyloudnorm — documentação e código](https://github.com/csteinmetz1/pyloudnorm): medição de loudness integrado.
- [Streamlit — st.audio](https://docs.streamlit.io/develop/api-reference/media/st.audio): reprodução na interface.

## Organização

```text
app.py                      Interface e gerenciamento da sessão
signal_lab/audio.py         Leitura, validação, prévias e WAV
signal_lab/analysis.py      STFT, bandas e métricas
signal_lab/dsp.py           Cálculo dos ganhos, filtros e validação
signal_lab/demo.py          Experimento sintético com referência conhecida
signal_lab/charts.py        Figuras com escalas e unidades
signal_lab/report.py        Tabela e relatórios JSON/CSV
signal_lab/presentation.py  Apresentação em seis etapas
signal_lab/cli.py           Execução pelo terminal
tests/                      Verificações de processamento e interface
```
