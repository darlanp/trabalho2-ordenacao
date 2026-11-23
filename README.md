# Trabalho 2 – Análise Experimental de Algoritmos de Ordenação

Disciplina de Análise de Algoritmos – FURB (Prof. Artur Ricardo Bizon).

Integrantes: Darlan Ramos Pereira, Thiago Rodrigo Schlei e Matheus Fernandes Cordeiro.

Implementação e análise experimental de **Quick Sort recursivo**, **Quick Sort iterativo** e
**Merge Sort** em Python, com cálculo do número de execuções (erro de 5% com 95% de confiança),
intervalos de confiança, ANOVA e teste de Tukey.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `src/algoritmos.py` | Implementação dos três algoritmos |
| `src/experimento.py` | Coleta dos tempos (amostragem inicial, cálculo do nº de execuções, experimento principal e escalabilidade) |
| `src/analise.py` | Estatísticas, intervalos de confiança, ANOVA, Tukey e gráficos |
| `tests/test_algoritmos.py` | Testes de corretude (compara com `sorted()`) |
| `dados/` | **Dados brutos dos experimentos em CSV** e descrição do ambiente (`ambiente.json`) |
| `resultados/` | Tabelas geradas pela análise (CSV) e `resumo.json` |
| `figuras/` | Gráficos usados no relatório |

### Arquivos CSV

- `dados/piloto.csv` – amostragem inicial (30 execuções por algoritmo, n = 100.000).
- `dados/tamanho_amostra.csv` – média, desvio padrão e número de execuções necessárias por algoritmo.
- `dados/experimento_principal.csv` – execuções definitivas (mesma entrada para os três algoritmos).
- `dados/escalabilidade.csv` – execuções para n = 10 mil, 50 mil, 100 mil, 200 mil e 400 mil.

Colunas dos CSVs de tempo: `fase, rodada, algoritmo, tamanho, tempo_s`.

## Como reproduzir

```bash
pip install -r requirements.txt
python tests/test_algoritmos.py   # corretude
python src/experimento.py         # coleta (alguns minutos)
python src/analise.py             # estatísticas, tabelas e figuras
```

A entrada é gerada com semente fixa (`SEMENTE = 2026`), portanto todos os algoritmos recebem
exatamente o mesmo vetor. Os tempos absolutos dependem da máquina; o ambiente usado está em
`dados/ambiente.json`.
