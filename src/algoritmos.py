"""Implementações dos algoritmos de ordenação avaliados no Trabalho 2.

Todos os algoritmos ordenam a lista recebida *in-place* (em ordem crescente)
e a devolvem, para facilitar o uso nos testes.

Os dois Quick Sorts usam exatamente o mesmo particionamento (esquema de
Hoare com pivô no elemento central). Assim, a única diferença entre eles é a
forma de controlar as subdivisões: chamadas recursivas ou pilha explícita.
"""

import sys

# A profundidade esperada da recursão é O(log n), mas aumentamos o limite
# para não haver falha em entradas desfavoráveis de tamanho moderado.
sys.setrecursionlimit(1_000_000)


# ---------------------------------------------------------------------------
# Particionamento compartilhado pelos dois Quick Sorts
# ---------------------------------------------------------------------------
def particionar(v, ini, fim):
    """Particionamento de Hoare com pivô no elemento central.

    Rearranja v[ini..fim] e devolve o índice j tal que todo elemento de
    v[ini..j] é <= pivô e todo elemento de v[j+1..fim] é >= pivô.
    """
    pivo = v[(ini + fim) // 2]
    i = ini - 1
    j = fim + 1
    while True:
        i += 1
        while v[i] < pivo:
            i += 1
        j -= 1
        while v[j] > pivo:
            j -= 1
        if i >= j:
            return j
        v[i], v[j] = v[j], v[i]


# ---------------------------------------------------------------------------
# Quick Sort recursivo
# ---------------------------------------------------------------------------
def _quick_rec(v, ini, fim):
    if ini < fim:
        p = particionar(v, ini, fim)
        _quick_rec(v, ini, p)
        _quick_rec(v, p + 1, fim)


def quick_sort_recursivo(v):
    """Quick Sort clássico, com duas chamadas recursivas por partição."""
    _quick_rec(v, 0, len(v) - 1)
    return v


# ---------------------------------------------------------------------------
# Quick Sort iterativo
# ---------------------------------------------------------------------------
def quick_sort_iterativo(v):
    """Quick Sort sem recursão, usando uma pilha explícita de intervalos.

    A cada partição o intervalo maior é empilhado primeiro, de modo que o
    menor seja processado antes; isso limita a pilha a O(log n) intervalos.
    """
    pilha = [(0, len(v) - 1)]
    while pilha:
        ini, fim = pilha.pop()
        if ini >= fim:
            continue
        p = particionar(v, ini, fim)
        if p - ini > fim - (p + 1):
            pilha.append((ini, p))
            pilha.append((p + 1, fim))
        else:
            pilha.append((p + 1, fim))
            pilha.append((ini, p))
    return v


# ---------------------------------------------------------------------------
# Merge Sort
# ---------------------------------------------------------------------------
def _intercalar(v, aux, ini, meio, fim):
    """Intercala v[ini..meio] e v[meio+1..fim] (já ordenados) usando aux."""
    aux[ini:fim + 1] = v[ini:fim + 1]
    i, j = ini, meio + 1
    for k in range(ini, fim + 1):
        if i > meio:
            v[k] = aux[j]
            j += 1
        elif j > fim:
            v[k] = aux[i]
            i += 1
        elif aux[j] < aux[i]:
            v[k] = aux[j]
            j += 1
        else:
            v[k] = aux[i]
            i += 1


def _merge_rec(v, aux, ini, fim):
    if ini < fim:
        meio = (ini + fim) // 2
        _merge_rec(v, aux, ini, meio)
        _merge_rec(v, aux, meio + 1, fim)
        _intercalar(v, aux, ini, meio, fim)


def merge_sort(v):
    """Merge Sort top-down (recursivo) com um único vetor auxiliar."""
    aux = [0] * len(v)
    _merge_rec(v, aux, 0, len(v) - 1)
    return v


ALGORITMOS = {
    "QuickSort_Recursivo": quick_sort_recursivo,
    "QuickSort_Iterativo": quick_sort_iterativo,
    "MergeSort": merge_sort,
}
