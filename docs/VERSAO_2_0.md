# Sinal 2.0 — recursos experimentais e protocolo de validação

A versão 2.0 estende a versão 1.2 sem modificar o núcleo STFT + equalização automática existente.

## Novos filtros
`signal_lab/advanced_filters.py` inclui passa-baixa e passa-alta Butterworth de segunda ordem e filtros shelving para graves e agudos (SOS biquad). Os coeficientes são gerados a partir de frequência, ganho e Q. Os filtros são adicionais; não substituem as dez bandas do equalizador original.

## Processamento por blocos
`signal_lab/streaming.py` conserva o estado dos filtros entre blocos de áudio. `tests/test_advanced.py` compara a saída por blocos com o processamento contínuo, confere estabilidade de polos e respostas. **Isso comprova continuidade DSP, não prova latência de hardware.**

## Demonstração experimental com microfone, SOMENTE em computador local
É necessário ter microfone, dispositivo de saída, sistema de áudio compatível e fones.

```bash
python -m pip install sounddevice
python -m signal_lab.live --enable-audio --seconds 10 --filter lowpass --cutoff 3000
```

O processo abre entrada e saída do dispositivo **apenas** quando `--enable-audio` está presente. O volume do sinal é reduzido no código, mas isso não dispensa baixar o volume físico. Interrompa com Ctrl+C. O programa não grava áudio e não deve ser executado no Codespaces, que normalmente não dispõe de dispositivo de áudio apropriado.

**Limites:** não se garante operação sem dropouts, dispositivo de baixa latência ou tempo real estrito. A callback usa código Python e aloca buffers; não é apropriada a utilização crítica. O ganho de entrada, latência de ida e volta e desempenho contínuo dependem do equipamento. Não altere filtros em tempo real nesta demonstração.

## Avaliação perceptiva
A avaliação auditiva requer **participantes e escuta real**. Para resultados defensáveis:
1. Selecione gravações autorizadas e classifique os gêneros / tipos.
2. Gere áudios processados com a mesma curva e salve os parâmetros.
3. Igualize loudness para comparação A/B (a equalização por RMS é apenas aproximação).
4. Faça uma avaliação cega aleatorizada, registrando preferência e comentários.
5. Relate quantos participantes avaliaram, condições de escuta e resultados, sem inferir significância quando a amostra for pequena.

Não há alegação de que um experimento perceptivo tenha sido executado; este documento define o protocolo, não seus resultados.

## Checklist de publicação
- Executar `python -m pytest -q` em ambiente com dependências instaladas.
- Executar `python scripts/validar_apresentacao.py`.
- Testar filtros em arquivos reais e escutar sem artefatos audíveis.
- Testar `signal_lab.live` em computador local, com dispositivos e limites de volume.
- Medir a latência e verificar ausência de dropouts; relatar valores reais.
- Registrar os resultados da avaliação perceptiva.

**Não integrar a 2.0 à main sem completar as verificações pertinentes.**
