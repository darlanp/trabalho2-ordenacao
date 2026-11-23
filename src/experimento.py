"""Execução dos experimentos do Trabalho 2.

Fases (todas gravam CSV em ../dados):
  1. piloto         - amostragem inicial (30 execuções por algoritmo, n = 100.000)
  2. tamanho        - cálculo do nº de execuções para erro de 5% com 95% de confiança
  3. principal      - execuções definitivas com a mesma entrada para os três algoritmos
  4. escalabilidade - complemento: tempos para diferentes tamanhos de entrada

Execução:  python src/experimento.py
"""

import csv
import gc
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime

from algoritmos import ALGORITMOS

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "dados")

SEMENTE = 2026            # semente fixa: todos usam exatamente a mesma entrada
N_PRINCIPAL = 100_000     # tamanho da entrada do experimento principal
AMOSTRA_PILOTO = 30       # execuções na amostragem inicial
ERRO_RELATIVO = 0.05      # erro máximo de 5% em relação à média
Z_95 = 1.959964           # quantil z(0,975) para 95% de confiança
MINIMO_EXECUCOES = 30     # piso usado mesmo que o cálculo indique menos
MAXIMO_EXECUCOES = 1000   # teto de segurança para o procedimento sequencial
TAMANHOS_ESCALA = [10_000, 50_000, 100_000, 200_000, 400_000]
EXECUCOES_ESCALA = 30
AQUECIMENTO = 2           # execuções descartadas antes de medir


def gerar_entrada(n, semente=SEMENTE):
    rng = random.Random(semente)
    return [rng.randint(0, 10**9) for _ in range(n)]


def medir(alg, entrada):
    """Tempo (s) de uma execução; a cópia da entrada fica fora da medição."""
    v = list(entrada)
    gc.collect()
    gc.disable()
    t0 = time.perf_counter()
    alg(v)
    t1 = time.perf_counter()
    gc.enable()
    return t1 - t0


def prioridade_alta():
    """Reduz a interferência de outros processos: prioridade alta e um único
    núcleo (evita migração entre núcleos). Afeta só este processo."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        proc = k32.GetCurrentProcess()
        k32.SetPriorityClass(proc, 0x00000080)        # HIGH_PRIORITY_CLASS
        k32.SetProcessAffinityMask(proc, 1 << 1)      # núcleo lógico 1
        return "prioridade alta, afinidade ao núcleo lógico 1"
    except Exception:
        try:
            os.sched_setaffinity(0, {1})
            return "afinidade ao núcleo 1"
        except Exception:
            return "padrão do sistema"


def rodar(entrada, execucoes, fase, rng_ordem, inicio=1, aquecer=True):
    """Executa os algoritmos em rodadas; em cada rodada a ordem é sorteada
    para que variações lentas do ambiente não favoreçam nenhum algoritmo."""
    if aquecer:
        esperado = sorted(entrada)
        for alg in ALGORITMOS.values():  # aquecimento + conferência de corretude
            for _ in range(AQUECIMENTO):
                v = list(entrada)
                alg(v)
                assert v == esperado
    linhas = []
    nomes = list(ALGORITMOS)
    for rodada in range(inicio, inicio + execucoes):
        rng_ordem.shuffle(nomes)
        for nome in nomes:
            t = medir(ALGORITMOS[nome], entrada)
            linhas.append({"fase": fase, "rodada": rodada, "algoritmo": nome,
                           "tamanho": len(entrada), "tempo_s": f"{t:.6f}"})
        print(f"  [{fase}] n={len(entrada)} rodada {rodada}/{inicio + execucoes - 1}", end="\r")
    print()
    return linhas


def salvar_csv(nome, linhas):
    caminho = os.path.join(DADOS, nome)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"  -> {os.path.normpath(caminho)}")


def tamanho_amostra(tempos):
    """n = (z * s / (r * média))^2, arredondado para cima."""
    media = statistics.mean(tempos)
    s = statistics.stdev(tempos)
    n = math.ceil((Z_95 * s / (ERRO_RELATIVO * media)) ** 2)
    return media, s, n


def ambiente():
    info = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "implementacao": platform.python_implementation(),
        "sistema": f"{platform.system()} {platform.release()} ({platform.version()})",
        "processador": platform.processor(),
        "semente": SEMENTE,
    }
    try:  # nome comercial do processador e memória no Windows
        import subprocess
        cpu = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor).Name; "
             "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)"],
            capture_output=True, text=True, timeout=60).stdout.split("\n")
        info["processador"] = cpu[0].strip()
        info["memoria_gb"] = cpu[1].strip().replace(",", ".")
    except Exception:
        pass
    return info


def calcular_n(linhas, etapa, fase):
    """Calcula, para cada algoritmo, o nº de execuções necessário (Eq. 1) e o
    erro relativo já obtido com as execuções disponíveis."""
    saida = []
    for nome in ALGORITMOS:
        tempos = [float(l["tempo_s"]) for l in linhas if l["algoritmo"] == nome]
        media, s, n = tamanho_amostra(tempos)
        erro = Z_95 * s / math.sqrt(len(tempos)) / media
        saida.append({"etapa": etapa, "base": fase, "algoritmo": nome,
                      "execucoes_disponiveis": len(tempos), "media_s": f"{media:.6f}",
                      "desvio_padrao_s": f"{s:.6f}", "erro_relativo_obtido": f"{erro:.4f}",
                      "erro_relativo_alvo": ERRO_RELATIVO, "confianca": 0.95, "z": Z_95,
                      "execucoes_necessarias": n})
        print(f"  {nome}: média={media:.4f}s s={s:.4f}s erro={100*erro:.1f}% -> n={n}")
    return saida


def main():
    os.makedirs(DADOS, exist_ok=True)
    rng_ordem = random.Random(SEMENTE + 1)
    info = ambiente()
    info["controle_processo"] = prioridade_alta()
    with open(os.path.join(DADOS, "ambiente.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    entrada = gerar_entrada(N_PRINCIPAL)

    print("1) Amostragem inicial")
    piloto = rodar(entrada, AMOSTRA_PILOTO, "piloto", rng_ordem)
    salvar_csv("piloto.csv", piloto)

    print("2) Cálculo do número de execuções")
    historico = calcular_n(piloto, 0, "piloto")
    execucoes = max(MINIMO_EXECUCOES, max(l["execucoes_necessarias"] for l in historico))
    print(f"  Execuções adotadas no experimento principal: {execucoes}")

    print("3) Experimento principal (sequencial: repete o cálculo até erro <= 5%)")
    principal = rodar(entrada, execucoes, "principal", rng_ordem)
    etapa = 1
    while True:
        atual = calcular_n(principal, etapa, "principal")
        historico += atual
        feitas = len(principal) // len(ALGORITMOS)
        if all(float(l["erro_relativo_obtido"]) <= ERRO_RELATIVO for l in atual):
            break
        alvo = min(MAXIMO_EXECUCOES, max(l["execucoes_necessarias"] for l in atual))
        if alvo <= feitas:
            break
        print(f"  Erro acima de 5%: ampliando de {feitas} para {alvo} execuções")
        principal += rodar(entrada, alvo - feitas, "principal", rng_ordem,
                           inicio=feitas + 1, aquecer=False)
        etapa += 1
    salvar_csv("tamanho_amostra.csv", historico)
    salvar_csv("experimento_principal.csv", principal)

    print("4) Escalabilidade")
    escala = []
    for n in TAMANHOS_ESCALA:
        escala += rodar(gerar_entrada(n), EXECUCOES_ESCALA, "escalabilidade", rng_ordem)
    salvar_csv("escalabilidade.csv", escala)
    print("Concluído.")


if __name__ == "__main__":
    main()
