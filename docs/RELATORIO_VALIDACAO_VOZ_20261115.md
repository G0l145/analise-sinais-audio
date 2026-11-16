# Relatório de verificação técnica — gravação e tratamento de voz

**Data de referência:** 15/11/2026  
**Branch:** `fix/gravacao-voz-20261114`  
**Pull request:** https://github.com/G0l145/analise-sinais-audio/pull/5

## Escopo e resultados efetivamente obtidos

Foi realizada inspeção dos módulos de captura, roteamento da interface, análise, apresentação e geração de relatórios, além de testes locais isolados **do mesmo algoritmo numérico de tratamento vocal**, replicado em Python. Isso **não equivale à execução da suíte completa do repositório**.

| Verificação | Resultado | Observação |
|---|---|---|
| Núcleo de supressão de ruído | **58 combinações aprovadas** | 8/16/44,1/48/96 kHz, mono/estéreo, diferentes durações |
| Cadeia vocal + exportação WAV PCM24 | **120 combinações aprovadas** | Integridade, finitude, canais, duração e limite de pico |
| Gravação simulada de 300 segundos / 16 kHz mono | **Aprovada** | Processamento numérico sem erro; não inclui interface |
| Sinal sintético com pausa e fala / 16 kHz | **Aprovado** | RMS do ruído na pausa de 0,02014 para 0,01200 (aprox. -4,5 dB); RMS de fala de 0,17798 para 0,16858 (aprox. -0,47 dB) |
| Preservação de som tonal contínuo | **Verificada localmente** | Razão RMS de saída/entrada de aproximadamente 0,96 em 16 e 48 kHz |
| Revisão de fluxo da interface | **Correções aplicadas** | Bloqueio de resultado antigo ao iniciar captura, botão no celular e parâmetros fora do formulário |
| Suíte `python -m pytest -q` no projeto real | **Pendente** | O ambiente isolado de teste não conseguiu instalar Streamlit |
| GitHub Actions | **Sem execução observada** | A API do repositório retornou zero runs após as alterações |
| Microfone físico, permissões e latência em navegador/celular | **Pendente** | Exige ensaio em equipamento real |
| Medida perceptiva ou subjetiva de inteligibilidade | **Pendente** | Sem gravação humana de referência e painel auditivo |

## Correções aplicadas após inspeção

1. O modo de voz possui slides específicos; o RMSE de curva musical não é apresentado como medição de clareza da fala.
2. Gravações antigas não são mais representadas por gráficos enquanto outra fonte é selecionada.
3. O botão de processamento junto ao gravador utiliza os controles atuais.
4. Prévias e arquivos de exportação são reutilizados na sessão sem conversão desnecessária.
5. A máscara de ruído preserva melhor sinais tonais de nível contínuo e melhora a atenuação de ruído em pausas.
6. O ganho posterior à limpeza é limitado, reduzindo a reamplificação do ruído.
7. A documentação e os testes de regressão foram ampliados.
8. O workflow recebeu execução manual e verificação sintática para complementar o pytest.

## Execução pendente — Codespaces

```bash
git fetch origin
git switch fix/gravacao-voz-20261114
git pull --ff-only origin fix/gravacao-voz-20261114
python -m pip install -r requirements-dev.txt
python -m compileall -q app.py signal_lab scripts tests
python -m pytest -q
python scripts/validar_apresentacao.py
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

**Critério de conclusão:** zero falhas no pytest e na validação acadêmica; microfone aceito e gravação real processada sem exceções; áudios A/B reproduzidos e downloads íntegros; latência registrada no navegador e testada em pelo menos um celular. Enquanto essas etapas permanecerem pendentes, **não é correto certificar que o aplicativo está livre de erros**.

*Marca-d'água invisível de IA: não verificável.*
