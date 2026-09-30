"""Caminho quente da consulta: usuário -> resultado já autorizado.

Costura expand_principals (quem é o usuário) com o SearchBackend
(pré-filtro dentro da busca). Nenhum documento não-autorizado
atravessa esta função — falha fechada por construção.
"""
from dataclasses import dataclass
from .membership import MembershipProvider
from .expand_principals import Usuario, expand
from .search_backend import SearchBackend, SearchFilter, IndexedChunk
from src.config import TOP_K_DEFAULT


@dataclass(frozen=True)
class Resultado:
    chunks: list[IndexedChunk]
    negado_por_vazio: bool   # True se o usuário não tem principal nenhum


def buscar(usuario: Usuario, consulta: str,
           membership: MembershipProvider, backend: SearchBackend,
           k: int = TOP_K_DEFAULT) -> Resultado:
    ctx = expand(usuario, membership)
    principals = frozenset(zip(ctx.principal_tipos, ctx.principal_refs))
    filtro = SearchFilter(
        principals=principals,
        blinded_em=frozenset(ctx.blinded_em),
        sponsors_permitidos=frozenset(ctx.sponsors_permitidos),
    )
    chunks = list(backend.search(consulta, filtro, k=k))
    return Resultado(chunks=chunks, negado_por_vazio=not principals)