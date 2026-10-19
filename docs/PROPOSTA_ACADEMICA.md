# Apresentação da proposta — Sinal

**Disciplina:** Análise de Sinais  
**Título:** Sistema de análise espectral e equalização automática de áudio  
**Instituição:** [preencher]  
**Integrantes:** [preencher]  
**Professor(a):** [preencher]

> **Natureza da apresentação:** demonstração da ideia, metodologia e viabilidade por meio de protótipo. Não é a entrega do trabalho final.

## 1. Problema
O equilíbrio espectral de diferentes gravações pode variar. Ajustar manualmente bandas de frequência exige conhecimento técnico e nem sempre segue um critério reproduzível.

## 2. Proposta
Criar uma aplicação que receba um arquivo de áudio, estime a potência por bandas de frequência e calcule uma equalização automática para aproximar o sinal de uma **curva-alvo escolhida**. O aplicativo permite ouvir, medir e exportar os resultados.

## 3. Como será realizado
1. **Entrada:** WAV ou FLAC; MP3 quando compatível com o decodificador.
2. **Medição:** STFT com janelas Hann e densidade espectral de potência.
3. **Agrupamento:** dez bandas de frequência, quando mensuráveis.
4. **Alvo:** referência, curva suave ou potência semelhante por banda.
5. **Correção:** filtros digitais IIR biquad com limite de ganho por filtro.
6. **Comparação:** remedição do erro relativo ao alvo e escuta A/B.
7. **Evidências:** gráficos, relatório e áudio de saída.

## 4. Protótipo demonstrável
A interface Streamlit já contém uma demonstração com áudio sintético gerado pelo próprio programa. O teste usa uma referência conhecida e uma versão propositalmente desequilibrada. Durante a apresentação, serão exibidos o erro antes/depois, o ganho aplicado e a escuta comparativa.

## 5. Critérios de validação
- Os testes automatizados devem passar.
- O sinal original deve ser preservado.
- A saída deverá manter duração, taxa de amostragem e quantidade de canais.
- No experimento sintético conhecido, o erro espectral relativo deverá diminuir.
- As exportações WAV, JSON e CSV devem ser geradas corretamente.
- A comparação A/B deverá ser audível no equipamento usado na sala.

**Limite da conclusão:** reduzir o erro em relação à curva-alvo não significa que toda música ficará subjetivamente melhor.

## 6. Escopo e possíveis evoluções
**Protótipo atual:** processamento offline, dez bandas, gráficos, comparação A/B e exportação de arquivos.

**Desenvolvimentos futuros (não implementados):** processamento em tempo real, avaliação auditiva controlada, medida de true peak e calibração para equipamentos.

## 7. Demonstração breve (5–7 minutos)
1. Problema e objetivo.
2. Etapas do processamento.
3. Espectro do sinal de teste.
4. Ganhos calculados automaticamente.
5. Escuta antes/depois e redução do erro.
6. Limitações e próximas etapas.

**Antes de apresentar:** execute `python scripts/validar_apresentacao.py` e confirme separadamente que o navegador e as caixas de som funcionam.

Materiais complementares: [roteiro detalhado](APRESENTACAO.md) e [metodologia](METODOLOGIA.md).
