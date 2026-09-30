"""Custo de contexto em tokens (controle de custo de RAG).

O custo dominante e controlável de um RAG é o CONTEXTO: cada chunk
recuperado vira token pago no prompt. Medimos isso para expor o
trade-off de k (mais candidatos = mais recall, mais token) e do
overlap do chunker (overlap = tokens redundantes pagos).

Contagem de token é INJETÁVEL (mesmo padrão do chunker). Default:
aproximação ~4 chars/token — zero dependência. Troca-se pelo tokenizer
real (tiktoken/o modelo de embedding) sem mudar a lógica.
"""
from dataclasses import dataclass
from typing import Callable
from src.config import PRECO_INPUT_USD_POR_1K



def aprox_tokens(texto: str) -> int:
    """~4 caracteres por token (regra de bolso p/ inglês/português).
    Aproximação para CI barato; trocar por tokenizer real em produção."""
    return max(1, len(texto) // 4) if texto else 0


@dataclass(frozen=True)
class CustoContexto:
    n_chunks: int
    tokens_total: int
    tokens_por_chunk: tuple[int, ...]


def custo_contexto(chunks_conteudo: list[str],
                   contar: Callable[[str], int] = aprox_tokens) -> CustoContexto:
    """Tokens que este conjunto de chunks adiciona ao prompt."""
    por_chunk = tuple(contar(c) for c in chunks_conteudo)
    return CustoContexto(
        n_chunks=len(chunks_conteudo),
        tokens_total=sum(por_chunk),
        tokens_por_chunk=por_chunk,
    )


def custo_estimado_usd(tokens: int, usd_por_1k: float = PRECO_INPUT_USD_POR_1K) -> float:
    """Custo em dólar do contexto. Default = preço do contrato no config.
    Editar PRECO_INPUT_USD_POR_1K em config.py atualiza todo cálculo."""
    return (tokens / 1000) * usd_por_1k