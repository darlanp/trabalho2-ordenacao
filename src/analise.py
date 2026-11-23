"""Análise estatística dos tempos medidos.

Lê os CSVs de ../dados e gera:
  - ../resultados/*.csv   tabelas (resumo, ICs, ANOVA, Tukey, escalabilidade)
  - ../resultados/resumo.json  todos os números usados no relatório
  - ../figuras/*.png      gráficos

Execução:  python src/analise.py
Dependências: numpy, pandas, scipy, matplotlib
"""

import itertools
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "dados")
RESULTADOS = os.path.join(BASE, "..", "resultados")
FIGURAS = os.path.join(BASE, "..", "figuras")

ORDEM = ["QuickSort_Recursivo", "QuickSort_Iterativo", "MergeSort"]
ROTULO = {"QuickSort_Recursivo": "Quick Sort recursivo",
          "QuickSort_Iterativo": "Quick Sort iterativo",
          "MergeSort": "Merge Sort"}
# Paleta categórica validada (slots 1-3, ordem fixa) + marcadores distintos,
# para que a identidade não dependa só da cor (impressão em tons de cinza).
COR = {"QuickSort_Recursivo": "#2a78d6", "QuickSort_Iterativo": "#eb6834",
       "MergeSort": "#1baf7a"}
MARCA = {"QuickSort_Recursivo": "o", "QuickSort_Iterativo": "s", "MergeSort": "^"}
TINTA, TINTA2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
CONF = 0.95
ERRO = 0.05

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 10, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRADE,
    "grid.linewidth": 0.6, "savefig.dpi": 220, "savefig.bbox": "tight",
})


def virgula(texto):
    """Separador decimal brasileiro nos rótulos dos gráficos."""
    return texto.replace(".", ",")


def ic_media(x, conf=CONF):
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    s = x.std(ddof=1)
    t = stats.t.ppf(1 - (1 - conf) / 2, n - 1)
    h = t * s / math.sqrt(n)
    return m, s, h, m - h, m + h, t


def resumo_grupos(df):
    linhas = []
    for alg in ORDEM:
        x = df.loc[df.algoritmo == alg, "tempo_s"].to_numpy()
        m, s, h, lo, hi, t = ic_media(x)
        z = stats.norm.ppf(1 - (1 - CONF) / 2)
        linhas.append({
            "algoritmo": alg, "execucoes": len(x), "media_s": m, "desvio_s": s,
            "cv_pct": 100 * s / m, "mediana_s": float(np.median(x)),
            "min_s": x.min(), "max_s": x.max(), "t_critico": t,
            "semiamplitude_s": h, "ic_inf_s": lo, "ic_sup_s": hi,
            "erro_relativo_obtido_pct": 100 * h / m,
            "execucoes_necessarias_recalc": math.ceil((z * s / (ERRO * m)) ** 2),
        })
    return pd.DataFrame(linhas)


def comparar_ics(res):
    linhas = []
    r = res.set_index("algoritmo")
    for a, b in itertools.combinations(ORDEM, 2):
        sobrepoe = not (r.at[a, "ic_sup_s"] < r.at[b, "ic_inf_s"]
                        or r.at[b, "ic_sup_s"] < r.at[a, "ic_inf_s"])
        linhas.append({"algoritmo_a": a, "algoritmo_b": b,
                       "ic_a": f"[{r.at[a, 'ic_inf_s']:.4f}; {r.at[a, 'ic_sup_s']:.4f}]",
                       "ic_b": f"[{r.at[b, 'ic_inf_s']:.4f}; {r.at[b, 'ic_sup_s']:.4f}]",
                       "intervalos_se_sobrepoem": sobrepoe,
                       "conclusao": ("inconclusivo pelos ICs" if sobrepoe else
                                     ("A mais rápido" if r.at[a, "media_s"] < r.at[b, "media_s"]
                                      else "B mais rápido"))})
    return pd.DataFrame(linhas)


def anova_tukey(df):
    grupos = [df.loc[df.algoritmo == a, "tempo_s"].to_numpy() for a in ORDEM]
    k = len(grupos)
    N = sum(len(g) for g in grupos)
    media_geral = np.concatenate(grupos).mean()
    sqe = sum(len(g) * (g.mean() - media_geral) ** 2 for g in grupos)  # entre grupos
    sqd = sum(((g - g.mean()) ** 2).sum() for g in grupos)               # dentro
    gl_e, gl_d = k - 1, N - k
    qme, qmd = sqe / gl_e, sqd / gl_d
    F = qme / qmd
    p = stats.f.sf(F, gl_e, gl_d)
    anova = pd.DataFrame([
        {"fonte": "Algoritmos", "SQ": sqe, "gl": gl_e, "QM": qme, "F": F,
         "F_critico": stats.f.ppf(CONF, gl_e, gl_d), "p_valor": p},
        {"fonte": "Erro (residual)", "SQ": sqd, "gl": gl_d, "QM": qmd},
        {"fonte": "Total", "SQ": sqe + sqd, "gl": N - 1},
    ])
    eta2 = sqe / (sqe + sqd)  # fração da variação explicada pelo algoritmo

    tk = stats.tukey_hsd(*grupos)
    ic = tk.confidence_interval(confidence_level=CONF)
    linhas = []
    for i, j in itertools.combinations(range(k), 2):
        linhas.append({
            "algoritmo_a": ORDEM[i], "algoritmo_b": ORDEM[j],
            "diferenca_media_s": tk.statistic[i, j],
            "ic_inf_s": ic.low[i, j], "ic_sup_s": ic.high[i, j],
            "p_valor": tk.pvalue[i, j],
            "diferenca_significativa": bool(tk.pvalue[i, j] < 1 - CONF),
        })
    # Diagnóstico das premissas da ANOVA
    lev = stats.levene(*grupos, center="median")
    shap = {a: float(stats.shapiro(g).pvalue) for a, g in zip(ORDEM, grupos)}
    kw = stats.kruskal(*grupos)
    premissas = {"levene_estatistica": float(lev.statistic), "levene_p": float(lev.pvalue),
                 "shapiro_p": shap, "kruskal_h": float(kw.statistic), "kruskal_p": float(kw.pvalue)}
    return anova, eta2, pd.DataFrame(linhas), premissas


def resumo_escala(df):
    linhas = []
    for (n, alg), g in df.groupby(["tamanho", "algoritmo"]):
        m, s, h, lo, hi, _ = ic_media(g.tempo_s)
        linhas.append({"tamanho": n, "algoritmo": alg, "execucoes": len(g),
                       "media_s": m, "desvio_s": s, "ic_inf_s": lo, "ic_sup_s": hi,
                       "erro_relativo_obtido_pct": 100 * h / m,
                       "media_por_nlogn_ns": 1e9 * m / (n * math.log2(n))})
    out = pd.DataFrame(linhas)
    out["ordem"] = out.algoritmo.map(ORDEM.index)
    return out.sort_values(["tamanho", "ordem"]).drop(columns="ordem")


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------
def fig_distribuicao(df, res, caminho):
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    rng = np.random.default_rng(0)
    for i, alg in enumerate(ORDEM):
        x = df.loc[df.algoritmo == alg, "tempo_s"].to_numpy() * 1000
        y = len(ORDEM) - 1 - i
        ax.boxplot(x, positions=[y], orientation="horizontal", widths=0.5, showfliers=False,
                   medianprops={"color": TINTA, "linewidth": 1.2},
                   boxprops={"color": TINTA2, "linewidth": 0.8},
                   whiskerprops={"color": TINTA2, "linewidth": 0.8},
                   capprops={"color": TINTA2, "linewidth": 0.8})
        ax.scatter(x, y + rng.uniform(-0.17, 0.17, len(x)), s=9, color=COR[alg],
                   marker=MARCA[alg], alpha=0.55, linewidths=0, zorder=3)
    ax.set_yticks(range(len(ORDEM)))
    ax.set_yticklabels([ROTULO[a] for a in reversed(ORDEM)])
    ax.set_xlabel("Tempo de execução (ms)")
    ax.grid(axis="y", visible=False)
    fig.savefig(caminho)
    plt.close(fig)


def fig_ics(res, caminho):
    fig, ax = plt.subplots(figsize=(6.2, 2.3))
    for i, row in res.iterrows():
        y = len(ORDEM) - 1 - ORDEM.index(row.algoritmo)
        ax.errorbar(row.media_s * 1000, y, xerr=row.semiamplitude_s * 1000,
                    fmt=MARCA[row.algoritmo], color=COR[row.algoritmo], ms=7,
                    capsize=5, elinewidth=2, capthick=2)
        ax.annotate(virgula(f"{row.media_s*1000:.1f} ms  [{row.ic_inf_s*1000:.1f}; "
                            f"{row.ic_sup_s*1000:.1f}]"),
                    (row.ic_sup_s * 1000, y), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=TINTA)
    ax.set_yticks(range(len(ORDEM)))
    ax.set_yticklabels([ROTULO[a] for a in reversed(ORDEM)])
    ax.set_ylim(-0.6, len(ORDEM) - 0.4)
    lo = res.ic_inf_s.min() * 1000
    hi = res.ic_sup_s.max() * 1000
    ax.set_xlim(lo - (hi - lo) * 0.08, hi + (hi - lo) * 0.45)
    ax.set_xlabel("Tempo médio (ms) com IC de 95%")
    ax.grid(axis="y", visible=False)
    fig.savefig(caminho)
    plt.close(fig)


def fig_tukey(tk, caminho):
    fig, ax = plt.subplots(figsize=(6.2, 2.1))
    nomes = {"QuickSort_Recursivo": "QS rec.", "QuickSort_Iterativo": "QS it.",
             "MergeSort": "Merge"}
    for i, row in tk.iterrows():
        y = len(tk) - 1 - i
        d = row.diferenca_media_s * 1000
        ax.errorbar(d, y, xerr=[[d - row.ic_inf_s * 1000], [row.ic_sup_s * 1000 - d]],
                    fmt="D", color=TINTA2, ms=5, capsize=4, elinewidth=1.6)
    ax.axvline(0, color=TINTA, linewidth=0.9, linestyle="--")
    ax.set_yticks(range(len(tk)))
    ax.set_yticklabels([f"{nomes[r.algoritmo_a]} − {nomes[r.algoritmo_b]}"
                        for r in tk.iloc[::-1].itertuples()])
    ax.set_xlabel("Diferença entre médias (ms) – IC simultâneo de 95% (Tukey)")
    ax.grid(axis="y", visible=False)
    fig.savefig(caminho)
    plt.close(fig)


def fig_escala(esc, caminho):
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.7))
    for alg in ORDEM:
        g = esc[esc.algoritmo == alg]
        n = g.tamanho.to_numpy() / 1000
        kw = dict(color=COR[alg], marker=MARCA[alg], ms=5, linewidth=2, label=ROTULO[alg])
        axs[0].plot(n, g.media_s.to_numpy(), **kw)
        axs[0].fill_between(n, g.ic_inf_s, g.ic_sup_s, color=COR[alg], alpha=0.18, linewidth=0)
        axs[1].plot(n, g.media_por_nlogn_ns.to_numpy(), **kw)
    axs[0].set_xlabel("Tamanho da entrada (mil elementos)")
    axs[0].set_ylabel("Tempo médio (s)")
    axs[1].set_xlabel("Tamanho da entrada (mil elementos)")
    axs[1].set_ylabel("Tempo / (n log₂ n)  (ns)")
    axs[1].set_ylim(bottom=0)
    from matplotlib.ticker import FuncFormatter
    axs[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: virgula(f"{v:.1f}")))
    axs[0].set_title("(a) tempo médio e IC de 95%", fontsize=9.5, color=TINTA)
    axs[1].set_title("(b) tempo normalizado por n log₂ n", fontsize=9.5, color=TINTA)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.07))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(caminho)
    plt.close(fig)


def main():
    os.makedirs(RESULTADOS, exist_ok=True)
    os.makedirs(FIGURAS, exist_ok=True)

    piloto = pd.read_csv(os.path.join(DADOS, "piloto.csv"))
    principal = pd.read_csv(os.path.join(DADOS, "experimento_principal.csv"))
    escala = pd.read_csv(os.path.join(DADOS, "escalabilidade.csv"))
    tam = pd.read_csv(os.path.join(DADOS, "tamanho_amostra.csv"))
    with open(os.path.join(DADOS, "ambiente.json"), encoding="utf-8") as f:
        amb = json.load(f)

    res_piloto = resumo_grupos(piloto)
    res = resumo_grupos(principal)
    cmp_ic = comparar_ics(res)
    anova, eta2, tk, premissas = anova_tukey(principal)
    esc = resumo_escala(escala)

    res.to_csv(os.path.join(RESULTADOS, "resumo_principal.csv"), index=False)
    cmp_ic.to_csv(os.path.join(RESULTADOS, "comparacao_ics.csv"), index=False)
    anova.to_csv(os.path.join(RESULTADOS, "anova.csv"), index=False)
    tk.to_csv(os.path.join(RESULTADOS, "tukey.csv"), index=False)
    esc.to_csv(os.path.join(RESULTADOS, "escalabilidade_resumo.csv"), index=False)

    fig_distribuicao(principal, res, os.path.join(FIGURAS, "fig1_distribuicao.png"))
    fig_ics(res, os.path.join(FIGURAS, "fig2_intervalos_confianca.png"))
    fig_tukey(tk, os.path.join(FIGURAS, "fig3_tukey.png"))
    fig_escala(esc, os.path.join(FIGURAS, "fig4_escalabilidade.png"))

    saida = {
        "ambiente": amb,
        "tamanho_amostra_piloto": tam.to_dict(orient="records"),
        "resumo_piloto": res_piloto.to_dict(orient="records"),
        "resumo_principal": res.to_dict(orient="records"),
        "comparacao_ics": cmp_ic.to_dict(orient="records"),
        "anova": anova.replace({np.nan: None}).to_dict(orient="records"),
        "eta2": eta2,
        "tukey": tk.to_dict(orient="records"),
        "premissas": premissas,
        "escalabilidade": esc.to_dict(orient="records"),
    }
    with open(os.path.join(RESULTADOS, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2, default=float)

    pd.set_option("display.width", 200)
    print(res.round(5).to_string(index=False))
    print(cmp_ic.to_string(index=False))
    print(anova.to_string(index=False), "\neta2 =", round(eta2, 4))
    print(tk.to_string(index=False))
    print(premissas)
    print(esc.round(5).to_string(index=False))


if __name__ == "__main__":
    main()
