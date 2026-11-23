"""Testes de corretude: compara cada algoritmo com sorted() do Python.

Execução:  python tests/test_algoritmos.py
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from algoritmos import ALGORITMOS  # noqa: E402


def casos():
    rng = random.Random(123)
    yield "vazio", []
    yield "um elemento", [7]
    yield "dois elementos", [2, 1]
    yield "todos iguais", [5] * 1000
    yield "ordenado", list(range(2000))
    yield "inverso", list(range(2000, 0, -1))
    yield "muitas repeticoes", [rng.randint(0, 9) for _ in range(5000)]
    yield "negativos", [rng.randint(-10**6, 10**6) for _ in range(5000)]
    for n in (3, 10, 101, 1000, 50_000):
        yield f"aleatorio n={n}", [rng.randint(0, 10**9) for _ in range(n)]


def main():
    falhas = 0
    for nome_caso, dados in casos():
        esperado = sorted(dados)
        for nome_alg, alg in ALGORITMOS.items():
            obtido = alg(list(dados))
            if obtido != esperado:
                falhas += 1
                print(f"FALHOU: {nome_alg} no caso '{nome_caso}'")
    if falhas:
        print(f"{falhas} falha(s).")
        sys.exit(1)
    print("Todos os testes passaram.")


if __name__ == "__main__":
    main()
