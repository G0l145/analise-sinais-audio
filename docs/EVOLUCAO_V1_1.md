# Evolução v1.1 — estabilidade e manutenção

Esta atualização preserva o algoritmo STFT/IIR existente e melhora a segurança operacional da interface:

- Os controles de processamento são reativos (fora de `st.form`), permitindo identificar alterações imediatamente.
- A alteração de parâmetros ou do arquivo de entrada suspende a exibição e os downloads até a próxima análise confirmada.
- Uma nova análise que falha descarta o resultado anterior para evitar associações incorretas.
- As prévias WAV são reutilizadas durante a navegação na mesma sessão, sendo recalculadas se mudar o resultado ou a configuração de comparação RMS.
- Três testes de interface verificam resultados obsoletos, falha após sucesso e reutilização de prévias.

## Validação obrigatória antes de integrar ao código principal

No Codespaces, com a branch selecionada e dependências instaladas:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/validar_apresentacao.py
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Teste manualmente (a) alterar intensidade sem clicar em analisar, (b) mudar para enviar áudio sem selecionar um arquivo, (c) retornar à demonstração sintética e executar novamente, (d) navegar entre abas e modo de apresentação. Verifique o áudio A/B e os arquivos WAV/JSON/CSV.

**Dependências:** `requirements.txt` define faixas de versões compatíveis, não um ambiente totalmente reproduzível. Antes de fixar versões exatas, gere e valide um lockfile em Python 3.11 e 3.12. Não introduzir pinos arbitrários sem essa validação.

**Limites:** cache em memória da sessão, não compartilhado entre usuários; testes de interface não substituem escuta real. Nenhuma alteração foi feita na matemática dos filtros.
