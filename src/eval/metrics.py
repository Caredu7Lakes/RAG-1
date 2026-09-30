"""Métricas de retrieval, determinísticas (sem LLM).

Avaliam a qualidade do ranking recuperado contra um golden set: para
cada pergunta, o conjunto de chunk_ids relevantes é conhecido.

IMPORTANTE: a avaliação roda sobre o resultado JÁ pré-filtrado (pós-ACL).
Mede retrieval dentro do que o usuário pode ver — recall sobre docs que
seriam barrados é ilusório.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CasoGolden:
    pergunta: str
    relevantes: frozenset[int]        # chunk_ids que DEVERIAM ser recuperados


def recall_at_k(recuperados: list[int], relevantes: frozenset[int],
                k: int) -> float:
    """Fração dos relevantes que apareceu no top-k. Sem relevantes -> 1.0
    (nada a recuperar = não penaliza)."""
    if not relevantes:
        return 1.0
    topk = set(recuperados[:k])
    return len(topk & relevantes) / len(relevantes)


def precision_at_k(recuperados: list[int], relevantes: frozenset[int],
                   k: int) -> float:
    """Fração do top-k que é relevante. Top-k vazio -> 0.0."""
    topk = recuperados[:k]
    if not topk:
        return 0.0
    return sum(1 for c in topk if c in relevantes) / len(topk)


def reciprocal_rank(recuperados: list[int], relevantes: frozenset[int]) -> float:
    """1/posição do primeiro relevante (1-indexado). Nenhum -> 0.0."""
    for i, c in enumerate(recuperados, start=1):
        if c in relevantes:
            return 1.0 / i
    return 0.0


@dataclass(frozen=True)
class Agregado:
    recall_at_k: float
    precision_at_k: float
    mrr: float
    n_casos: int


def avaliar(resultados: list[tuple[CasoGolden, list[int]]], k: int) -> Agregado:
    """Média das métricas sobre todos os casos.
    resultados = [(caso, chunk_ids recuperados p/ aquele caso), ...]."""
    if not resultados:
        return Agregado(0.0, 0.0, 0.0, 0)

    n = len(resultados)
    rec = sum(recall_at_k(r, c.relevantes, k) for c, r in resultados) / n
    prec = sum(precision_at_k(r, c.relevantes, k) for c, r in resultados) / n
    mrr = sum(reciprocal_rank(r, c.relevantes) for c, r in resultados) / n
    return Agregado(recall_at_k=rec, precision_at_k=prec, mrr=mrr, n_casos=n)