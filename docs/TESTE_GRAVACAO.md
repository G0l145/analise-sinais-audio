# Testar gravação e equalização

## Preparar o Codespaces

Abra o terminal na pasta `/workspaces/analise-sinais-audio` e execute:

```bash
git status --short
git fetch origin
git switch fix/gravacao-voz-20261114
git pull --ff-only origin fix/gravacao-voz-20261114
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
| 4 | Manter **Voz nítida · limpeza e realce**, clicar em **Analisar e equalizar** | O resultado identifica `gravacao_microfone.wav`, com duração, taxa e canais |
| 5 | Ouvir **A · Antes** e **B · Depois** na aba **Visão geral** | Os dois áudios podem ser reproduzidos; comparar com volume baixo |
| 6 | Baixar o WAV equalizado, JSON e CSV | Os três arquivos são baixados e abrem sem erro |
| 7 | Fazer outra gravação | A interface avisa que o resultado ainda pertence à análise anterior |
| 8 | Clicar novamente em **Analisar e equalizar** | O resultado passa a corresponder à nova gravação |
| 9 | Selecionar **Áudio de referência**, enviar um WAV e analisar | A referência é usada e identificada no resultado |

O aplicativo processa a gravação **depois** de encerrada, ao clicar em **Analisar e equalizar**. Ganhos nulos ou diferenças discretas podem ocorrer: a correção depende do áudio, do alvo e das bandas mensuráveis. O modo Voz nítida atenua parte de ruídos estacionários; não garante eliminar eco, ruído impulsivo ou distorções já existentes.

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


## Verificação da nova limpeza e da experiência no celular

1. Abra a página HTTPS no navegador do celular e selecione **Gravar áudio**.
2. Observe se o gravador aparece na página principal; conceda a permissão quando solicitado. Registre o intervalo entre tocar em gravar e o início visível da captura. A latência depende do navegador e não há promessa de início instantâneo.
3. Grave pelo menos 10 segundos de fala com um ventilador ou outra fonte leve de ruído constante ao fundo, mantendo distância fixa do microfone.
4. Encerre e clique em **Analisar e equalizar** com **Voz nítida · limpeza e realce** selecionado.
5. Confirme que não há exceção, que o nome da gravação aparece, e que a escuta **Antes/Depois** funciona. Observe se o ruído durante pausas diminui e se as palavras permanecem compreensíveis.
6. Confira os três downloads, os filtros, as notas técnicas e o relatório JSON. Para Voz nítida, o RMSE musical deve ser `null`; isso é intencional.
7. Selecione **Curva suave** e processe novamente o mesmo áudio para comparar o modo musical com o tratamento dedicado à fala.
8. Repita com gravação silenciosa, trecho curto e nova gravação. A versão anterior deve continuar acessível quando houver erro de entrada, sem substituir um resultado válido.

Para rodar somente as verificações novas:

```bash
python -m pytest -q tests/test_voice.py tests/test_recording.py tests/test_app.py
```

As verificações automatizadas não medem a latência física do microfone nem substituem escuta humana. Anote navegador, dispositivo, duração, mensagens de erro e tempo de processamento.


## Verificação visual da troca de modos (16/11/2026)

1. Inicie o sistema e observe o gráfico da demonstração. Selecione **Curva suave** e depois **Mesma potência por banda**. Sem clicar em **Analisar e equalizar**, confirme que os números, a curva-alvo, a saída e a dupla de cores mudaram.
2. Selecione **Gravar áudio**, grave e processe uma frase de 8–10 segundos. Altere **Voz nítida → Curva suave → Mesma potência por banda → Voz nítida**. Cada mudança deve atualizar o gráfico e as métricas automaticamente, sem novo clique.
3. Confira as cores em cada modo e diferencie as curvas pelos símbolos (círculo antes, quadrado depois) e pelo tracejado do alvo.
4. Troque para uma fonte sem áudio. O gráfico anterior não deve aparecer como resultado da nova fonte.
5. Selecione **Áudio de referência** sem fornecer a referência: o aplicativo deve informar que o arquivo é necessário e não reutilizar o resultado anterior.
6. Aumente o zoom do navegador para verificar legendas, bandas e eixos. Em celular, confira a rolagem, a legibilidade e os dois áudios A/B.
7. Altere apenas a **intensidade da correção**: o sistema deve solicitar o clique no botão de processamento antes de atualizar o resultado (comportamento previsto).

**Validação automatizada:** executar `python -m pytest -q` e verificar testes de interface (`tests/test_app.py`) e visualização (`tests/test_charts.py`). A validação num navegador e microfone físicos continua necessária para homologação.
