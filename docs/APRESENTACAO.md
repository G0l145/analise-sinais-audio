# Roteiro para apresentação ao professor

Abra o aplicativo, mantenha **Demonstração pronta** e **Áudio de referência**, intensidade **0,85**, Q **1,4** e limite por filtro **±6 dB**. Ative **Igualar RMS na escuta A/B** e **Modo de apresentação ao professor**. As seis etapas usam os resultados reais da sessão.

## 1. Objetivo — cerca de 40 segundos

“O projeto analisa um arquivo de áudio e ajusta automaticamente seu equilíbrio espectral em dez bandas. Para avaliar a correção, definimos um alvo e medimos o erro antes e depois.”

Explique que um alvo precisa ser explícito: a mesma curva não é ideal para todos os gêneros, gravações e equipamentos.

## 2. Método — cerca de 40 segundos

Mostre as etapas de entrada, STFT, escolha do alvo, cálculo dos ganhos, aplicação dos filtros e comparação. A implementação usa Python e bibliotecas de processamento de sinais; a interface executa no navegador.

## 3. Análise — cerca de 60 segundos

Apresente o uso da Hann periódica, da sobreposição de 50% e da PSD unilateral. Destaque que os canais são combinados por média de potência, evitando cancelamento em estéreo. Explique a integração da PSD em cada banda.

Se perguntarem por FFT e STFT: FFT é o algoritmo usado para calcular a DFT; STFT aplica essa transformada a janelas deslocadas no tempo e permite montar o espectrograma.

## 4. Correção — cerca de 60 segundos

Mostre os ganhos efetivos. Explique a subtração da média dos níveis de banda, a diferença entre alvo e entrada, a intensidade, a suavização e o limite. Mostre a representação dos biquads IIR em SOS.

Esclareça que o limite de ±6 dB é por filtro. A resposta combinada depende da sobreposição, e a saída é medida novamente antes da aceitação da correção.

## 5. Experimento — cerca de 90 segundos

1. Explique que a referência sintética é gerada pelo próprio sistema, sem material musical de terceiros.
2. Mostre a entrada com desequilíbrio conhecido e os valores reais do erro.
3. Reproduza alguns segundos de **Antes**; pause antes de reproduzir **Depois**.
4. Relacione a mudança percebida com a mudança das curvas de banda.
5. Volte ao laboratório, se necessário, para mostrar forma de onda, PSD e espectrogramas.
6. Mostre as opções de exportação WAV, JSON e CSV.

Não reproduza os dois players simultaneamente, porque isso soma os sinais e prejudica a comparação. A igualação por RMS reduz o efeito do volume, mas não garante loudness percebido idêntico.

## 6. Conclusão — cerca de 40 segundos

Apresente a aproximação medida ao alvo e os limites: alteração de fase e transientes do IIR, processamento offline, alvo dependente do objetivo musical e proteção somente de pico de amostras.

Não conclua que a saída é “sempre melhor”. A conclusão sustentada pelo experimento é que a saída ficou mais próxima do alvo no critério espectral adotado.

## Perguntas prováveis

| Pergunta | Resposta técnica |
|---|---|
| Por que dez bandas? | Oferecem um conjunto didático que cobre graves, médios e agudos com centros aproximadamente logarítmicos. |
| A equalização é IA? | O MVP usa processamento determinístico e regras matemáticas. Não há modelo de aprendizado de máquina. |
| Equilibrar bandas torna a PSD plana? | Não. Bandas mais largas integram mais frequências; potência por oitava e PSD plana são critérios diferentes. |
| A potência estéreo é somada? | Usa-se a média da potência dos canais, preservando a escala e evitando cancelamento por fase. |
| E se o áudio tiver clipping? | A saída tem proteção de pico, mas uma equalização não recupera distorção já presente na entrada. |
| Por que o erro pode ficar igual? | Correções que pioram o critério são reduzidas; em casos inadequados, o ganho pode retornar a zero. |
| Por que há bandas desativadas? | Podem estar próximas ou acima de Nyquist, sem bins úteis ou sem energia suficiente. |
| É um normalizador de volume? | A finalidade é ajuste espectral. A atenuação protege picos e as prévias podem ter RMS igualado. |
| LUFS e RMS são a mesma coisa? | Não. RMS mede energia média; LUFS inclui ponderação e integração de loudness. |
| O arquivo original é alterado? | Não. O sistema gera uma saída separada e mantém o original. |

## Verificação antes da aula

- Abra o Codespace ou o ambiente local e carregue a demonstração.
- Teste a reprodução e o dispositivo de saída de áudio.
- Em uma sala sem conectividade, prefira a execução local previamente instalada.
- Confira os resultados do teste com `python -m pytest -q`.
- Se quiser resultados exportados, use `python -m signal_lab.cli demo --out resultados/apresentacao-01`.
