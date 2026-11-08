# Testar gravação e equalização

## Preparar o Codespaces

Abra o terminal na pasta `/workspaces/analise-sinais-audio` e execute:

```bash
git status --short
git fetch origin
git switch codex/gravacao-microfone
git pull --ff-only origin codex/gravacao-microfone
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Se o Git informar alterações locais que impedem a troca de branch, preserve-as antes de continuar. Não use `reset --hard`. Se os testes falharem, registre a saída do terminal antes do ensaio.

Abra a aba **Ports**, localize **8501** e escolha **Open in Browser**. Use a página externa em HTTPS para testar o microfone. Se a porta estiver ocupada por outra execução, encerre o Streamlit anterior com `Ctrl+C` no terminal correspondente.

## Ensaio com microfone real

| Etapa | Ação | Resultado esperado |
|---|---|---|
| 1 | Escolher **Gravar áudio** e iniciar o gravador | O navegador solicita permissão; o gravador indica a captura |
| 2 | Gravar 10–20 segundos de fala e encerrar | A gravação aparece no gravador e pode ser ouvida |
| 3 | Baixar **Gravação original · WAV** | O navegador baixa o áudio capturado, antes de qualquer correção |
| 4 | Manter **Curva suave**, clicar em **Analisar e equalizar** | O resultado identifica `gravacao_microfone.wav`, com duração, taxa e canais |
| 5 | Ouvir **A · Antes** e **B · Depois** na aba **Visão geral** | Os dois áudios podem ser reproduzidos; comparar com volume baixo |
| 6 | Baixar o WAV equalizado, JSON e CSV | Os três arquivos são baixados e abrem sem erro |
| 7 | Fazer outra gravação | A interface avisa que o resultado ainda pertence à análise anterior |
| 8 | Clicar novamente em **Analisar e equalizar** | O resultado passa a corresponder à nova gravação |
| 9 | Selecionar **Áudio de referência**, enviar um WAV e analisar | A referência é usada e identificada no resultado |

O aplicativo processa a gravação **depois** de encerrada, ao clicar em **Analisar e equalizar**. Ganhos nulos ou diferenças discretas podem ocorrer: a correção depende do áudio, do alvo e das bandas mensuráveis. Equalização não remove necessariamente ruído, eco ou distorção que já existam na gravação.

### Casos de erro

- **Sem gravação:** em uma sessão nova, selecionar **Gravar áudio** e clicar em **Analisar e equalizar** deve pedir que grave e encerre um áudio.
- **Permissão negada:** negar acesso não deve iniciar a captura. Para repetir, liberar o microfone nas permissões do site e do sistema e recarregar a página.
- **Microfone incorreto:** conferir o dispositivo selecionado no navegador e no sistema. Uma gravação silenciosa pode ser processada, mas não comprova que o microfone funciona.
- **Limite excedido:** não ultrapassar 5 minutos/50 MB. Os limites são verificados ao ler a gravação, sem garantia de parada automática do gravador.
- **Referência ausente:** escolher o alvo de referência sem enviar arquivo deve mostrar uma orientação, preservando o último resultado válido.

## Testar pelo celular

1. Com o Streamlit em execução no Codespaces, copie o endereço HTTPS mostrado para a porta **8501**.
2. Abra esse endereço no navegador do celular e autentique-se com a mesma conta GitHub se solicitado. A porta pode permanecer **Private**.
3. Permita acesso ao microfone do celular e siga o ensaio acima. A captura usa o dispositivo que abriu a página.
4. Mantenha o Codespace ligado durante o teste. Ao terminar, encerre o Streamlit e pare o Codespace.

## Testar o processamento sem microfone

Para gerar amostras sintéticas PCM16 mono a 16 e 48 kHz e uma amostra silenciosa:

```bash
python scripts/gerar_audios_teste.py --out resultados/amostras-gravacao
```

O gerador usa somente a biblioteca padrão do Python e recusa sobrescrever a pasta. Se ela já existir, escolha outro nome.

Na interface, selecione **Enviar áudio** e teste cada WAV. Para um ensaio pelo terminal:

```bash
python -m signal_lab.cli equalize resultados/amostras-gravacao/multibanda_48000Hz.wav --target gentle --out resultados/equalizacao-gravacao
```

Esses arquivos verificam o caminho de leitura e equalização, sem provar acesso ao microfone. Comece a escuta em volume baixo.

## Testes automatizados

```bash
python -m pytest -q tests/test_recording.py tests/test_app.py
```

Os testes de processamento simulam WAV PCM16 a 16, 44,1 e 48 kHz, com sinal e silêncio, e verificam preservação da entrada, taxa, duração/canais, finitude, teto de pico, WAV PCM24 e relatórios. Os testes de interface simulam o retorno do gravador e verificam ausência de captura, dados inválidos, referência e atualização de resultado.

Para validar o restante do projeto, execute também `python -m pytest -q`. Os testes simulados não verificam a permissão do navegador nem o hardware; esses itens dependem do ensaio real.

## Registrar o ensaio

Anote o navegador/dispositivo, duração e taxa recebidas, alvo escolhido, erro antes/depois e se os downloads e a escuta funcionaram. Para compartilhar uma falha, envie a mensagem exibida e o trecho do terminal; use uma gravação sem dados pessoais. A aplicação mantém os áudios em memória no ambiente de execução e não os envia ao GitHub. Os downloads ficam no dispositivo do usuário. Não faça commit de gravações pessoais; use `audios-pessoais/` ou `resultados/`, ignorados pelo Git.
