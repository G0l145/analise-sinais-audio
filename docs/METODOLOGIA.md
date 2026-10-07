# Metodologia do experimento

## 1. Objetivo e hipótese

Implementar equalização automática de arquivos mono/estéreo com critério espectral explícito. Para uma referência conhecida, espera-se que a correção reduza o erro da forma espectral por bandas sem alterar taxa, duração ou canais.

O alvo não representa uma verdade musical universal. Músicas, gêneros e equipamentos podem justificar equilíbrios diferentes. O sistema mede aproximação ao alvo escolhido; a avaliação subjetiva exige escuta e, idealmente, comparação cega.

## 2. Preparação e STFT

O áudio é decodificado como `float64` com dimensões `(amostras, canais)`. Taxa, tamanho, duração, número de canais e finitude são verificados antes do processamento. Em arquivos, o cabeçalho é inspecionado antes de alocar os dados decodificados.

Usa-se uma Hann periódica `w[n]`, com `N` igual a 8.192 ou à maior potência de dois que cabe em um áudio menor. O salto é `H = N/2`.

```math
X_c(m,k)=\sum_{n=0}^{N-1}x_c[n+mH]w[n]e^{-j2\pi kn/N}
```

A densidade espectral de potência unilateral é:

```math
P_c(m,k)=\frac{d_k|X_c(m,k)|^2}{f_s\sum_n w[n]^2}
```

O fator `dₖ` vale 2 nos bins internos e 1 em DC e Nyquist. Calcula-se a média em potência de todas as janelas completas e dos canais. Somar canais em amplitude antes da FFT poderia cancelar sinais em oposição de fase; essa soma não é usada.

O passo entre bins é `Δf = fs/N`. A resolução efetiva também depende da janela. A cauda que não completa uma janela fica fora da análise espectral, mas permanece no áudio filtrado e nas métricas globais. O JSON informa a quantidade de amostras dessa cauda.

## 3. Potência por banda

Os dez centros são 31,5; 63; 125; 250; 500; 1.000; 2.000; 4.000; 8.000; 16.000 Hz. As fronteiras intermediárias são médias geométricas de centros vizinhos, formando bandas aproximadamente de uma oitava. As fronteiras extremas usam os fatores `1/√2` e `√2`.

```math
E_i=\sum_{k\in B_i}\overline{P}(k)\Delta f,\qquad M_i=10\log_{10}(\max(E_i,10^{-20}))
```

Uma banda só é usada quando contém bins, seu centro está abaixo de `0,45·fs` e sua potência supera `max(10⁻²⁰, 10⁻⁷·Emax)`. No modo referência, ela também precisa ser mensurável na referência. São necessárias pelo menos duas bandas para calcular uma forma espectral relativa.

Os modos matemáticos são a mesma potência por banda ou uma inclinação de −1 dB por oitava. No modo referência, `Tᵢ` é o nível de banda medido no outro áudio. Referências podem ter duração e taxa diferentes: a comparação usa frequências físicas e a interseção das bandas disponíveis.

## 4. Ganhos e filtros

Centralizar os níveis permite comparar a forma sem confundir volume global e equilíbrio espectral:

```math
\widetilde M_i=M_i-\langle M\rangle_B,\quad \widetilde T_i=T_i-\langle T\rangle_B
```

```math
G_i=\operatorname{clip}\left(\alpha\operatorname{suavizar}(\widetilde T_i-\widetilde M_i),-G_{max},G_{max}\right)
```

`α` está entre 0 e 1 e `Gmax` entre 0 e 6 dB. A suavização usa os pesos ¼, ½ e ¼, renormalizados quando um vizinho está excluído. Ganhos de bandas excluídas são zero.

São utilizados filtros **peaking biquad** de Robert Bristow-Johnson, conforme o Audio EQ Cookbook/W3C, representados em SOS com `a₀ = 1`:

```math
H_i(z)=\frac{b_0+b_1z^{-1}+b_2z^{-2}}{1+a_1z^{-1}+a_2z^{-2}},\quad H(z)=\prod_iH_i(z)
```

O parâmetro `Q` controla a largura dos filtros. O mesmo filtro é aplicado separadamente a cada canal. A fase é alterada pelo IIR e podem existir transientes no início. O limite é por filtro: a sobreposição pode produzir uma resposta total maior que ±6 dB.

## 5. Remedição e proteção

```math
\mathrm{RMSE}=\sqrt{\frac{1}{|B|}\sum_{i\in B}(\widetilde M_i-\widetilde T_i)^2}
```

A saída é analisada com o mesmo método e a mesma máscara de bandas da comparação inicial. Se a correção completa piorar o erro, o sistema testa metade dos ganhos e, se necessário, ganho zero. A tolerância numérica é `10⁻⁸ dB`. Esse mecanismo protege o critério medido, sem garantir percepção sonora superior.

Para respeitar o teto `C` de pico de amostras, aplica-se uma escala global:

```math
s=\min\left(1,\frac{10^{C/20}}{\max_n|y[n]|}\right)
```

Em silêncio, `s = 1`. A escala somente atenua, com teto padrão de −1 dBFS. Não mede picos entre amostras e não é um limitador de true peak.

## 6. Escuta, métricas e exportação

RMS é calculado sobre as amostras e canais; o pico é o maior módulo entre eles. LUFS integrado é medido por pyloudnorm quando há duração suficiente e energia. Silêncio produz valores indisponíveis, representados como `null` em JSON.

Para A/B com RMS igualado, cada prévia é atenuada até o menor RMS dos dois sinais. Uma escala comum adicional evita ultrapassar −1 dBFS. As prévias não alteram as métricas nem o WAV exportado. RMS igualado não garante loudness percebido idêntico.

A exportação usa WAV PCM de 24 bits, preservando quantidade de amostras, taxa e canais. Há quantização de até aproximadamente um passo de 24 bits. O JSON registra parâmetros, potências, ganhos, RMSE, atenuação, métricas e coeficientes SOS; não armazena o conteúdo completo do áudio.

## 7. Experimento reproduzível

O gerador produz 12 segundos de percussão, baixo, melodia e fundo espectral rosa com semente 42. Essa mistura é a referência. Uma cascata conhecida altera o equilíbrio entre graves e agudos para formar a entrada de teste. O modo referência busca corrigir essa alteração.

Como os filtros interagem e o ganho é suavizado e limitado, não se espera recuperação matemática exata da referência. Os testes exigem redução substancial do erro e preservação das propriedades do áudio. As medições efetivas aparecem na interface e no relatório, evitando números fixos na apresentação.

## Referências

- https://www.w3.org/TR/audio-eq-cookbook/
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfilt.html
- https://github.com/csteinmetz1/pyloudnorm
