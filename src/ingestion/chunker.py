"""Documento -> chunks (§6, tabela chunk).

Chunking é decisão de trade-off, não regra fixa — por isso Strategy:
uma estratégia concreta agora (janela deslizante com overlap), com o
seam para trocar por semantic/recursive/token-based sem tocar no resto
da ingestão.

Tamanho é medido por uma FUNÇÃO DE COMPRIMENTO injetável (default: nº
de caracteres). Em produção troca-se por um contador de tokens do
tokenizer do modelo de embedding — sem mudar a lógica de janela.
"""
from dataclasses import dataclass
from typing import Protocol, Callable


@dataclass(frozen=True)
class Chunk:
    """Espelha a tabela chunk: (documento_id, ordem, conteudo)."""
    ordem: int
    conteudo: str


class ChunkStrategy(Protocol):
    def split(self, texto: str) -> list[str]: ...


class FixedSizeChunker:
    """Janela deslizante de tamanho fixo com overlap.

    tamanho  = alvo de cada chunk (na unidade da função de comprimento).
    overlap  = quanto o próximo chunk repete do anterior, para não
               cortar contexto na fronteira (recall na borda).
    """

    def __init__(self, tamanho: int = 800, overlap: int = 100,
                 comprimento: Callable[[str], int] = len):
        if overlap >= tamanho:
            raise ValueError("overlap deve ser menor que tamanho")
        self._tamanho = tamanho
        self._overlap = overlap
        self._comprimento = comprimento

    def split(self, texto: str) -> list[str]:
        texto = texto.strip()
        if not texto:
            return []
        if self._comprimento(texto) <= self._tamanho:
            return [texto]

        passo = self._tamanho - self._overlap
        chunks: list[str] = []
        inicio = 0
        while inicio < len(texto):
            fim = inicio + self._tamanho
            pedaco = texto[inicio:fim].strip()
            if pedaco:
                chunks.append(pedaco)
            if fim >= len(texto):
                break
            inicio += passo
        return chunks


def chunk_documento(documento_id: int, texto: str,
                    strategy: ChunkStrategy) -> list[Chunk]:
    """Aplica a estratégia e numera os chunks (ordem estável)."""
    return [
        Chunk(ordem=i, conteudo=pedaco)
        for i, pedaco in enumerate(strategy.split(texto))
    ]