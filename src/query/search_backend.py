"""Contrato do backend de busca vetorial (Azure AI Search) + mock.

O pré-filtro de ACL entra DENTRO da busca (§4): o backend recebe os
principals e atributos ABAC como filtro e só devolve candidatos JÁ
autorizados. Pós-filtrar (buscar e depois descartar) machuca recall
e pode vazar em borda.
"""
from dataclasses import dataclass
from typing import Protocol, Iterable


@dataclass(frozen=True)
class IndexedChunk:
    """Um chunk no índice, com a ACL replicada do Postgres (§4)."""
    id: int
    documento_id: int
    ordem: int
    conteudo: str
    setor: str
    # ACL replicada como pares (tipo, ref) — espelha documento_acl
    principals: frozenset[tuple[str, str]]
    # ABAC replicado (nulo fora do regulado)
    estudo_ref: str | None = None
    blinding: str | None = None
    sponsor_ref: str | None = None


@dataclass(frozen=True)
class SearchFilter:
    """Filtro aplicado dentro da busca. Vem do QueryContext."""
    principals: frozenset[tuple[str, str]]
    blinded_em: frozenset[str]
    sponsors_permitidos: frozenset[str]


class SearchBackend(Protocol):
    """Azure AI Search (real) e o mock satisfazem isto."""
    def search(self, consulta: str, filtro: SearchFilter,
               k: int = 10) -> Iterable[IndexedChunk]: ...


class SearchBackendMock:
    """Simula a busca ANN com pré-filtro. Sem vetores: casa por substring
    na consulta — suficiente para exercitar a lógica de ACL.

    Implementa IndiceMutavel (eventhub_sync): a ACL fica num dict lateral
    mutável, para que uma revogação por evento apague o acesso e a busca
    seguinte já não retorne o doc. Fecha o loop revogação -> busca (§4).
    """

    def __init__(self, chunks: list[IndexedChunk]):
        self._chunks = chunks
        # ACL mutável, separada do chunk imutável: doc_id -> {(tipo, ref)}
        self._acl: dict[int, set[tuple[str, str]]] = {}
        for c in chunks:
            self._acl.setdefault(c.documento_id, set()).update(c.principals)

    # --- busca (caminho quente) ---

    def search(self, consulta: str, filtro: SearchFilter, k: int = 10):
        termo = consulta.lower()
        autorizados = (
            c for c in self._chunks
            if self._passa_acl(c, filtro)
            and self._passa_abac(c, filtro)
            and self._passa_sponsor(c, filtro)
        )
        relevantes = (c for c in autorizados if termo in c.conteudo.lower())
        return list(relevantes)[:k]

    def _passa_acl(self, c: "IndexedChunk", f: SearchFilter) -> bool:
        # consulta a ACL LATERAL (mutável), não o campo do chunk
        return bool(self._acl.get(c.documento_id, set()) & f.principals)

    @staticmethod
    def _passa_abac(c: "IndexedChunk", f: SearchFilter) -> bool:
        if c.blinding == "unblinded" and c.estudo_ref in f.blinded_em:
            return False
        return True

    @staticmethod
    def _passa_sponsor(c: "IndexedChunk", f: SearchFilter) -> bool:
        if c.sponsor_ref is None:
            return False
        return c.sponsor_ref in f.sponsors_permitidos

    # --- IndiceMutavel (recebe eventos de eventhub_sync) ---

    def add_principal(self, documento_id: int, principal: tuple[str, str]) -> None:
        self._acl.setdefault(documento_id, set()).add(principal)

    def remove_principal(self, documento_id: int, principal: tuple[str, str]) -> None:
        self._acl.get(documento_id, set()).discard(principal)

    def remove_documento(self, documento_id: int) -> None:
        self._acl.pop(documento_id, None)