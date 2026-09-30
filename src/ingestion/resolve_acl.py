"""Resolve ACL crua da fonte -> principals para o pré-filtro.

Fronteira de segurança do sistema. Regras:
  - Só concessões de LEITURA viram principal (edit/full incluem read).
  - Herança e marcadores especiais são resolvidos aqui, na ingestão,
    nunca em tempo de consulta (§1 do MD).
  - Falha fechada: na dúvida, NÃO emite principal.
"""
from dataclasses import dataclass
from typing import Iterable, Literal
from src.sources.base import SourceDocument, Grant

# Níveis que concedem leitura. 'edit' e 'full' incluem 'read'.

NIVEIS_DE_LEITURA = frozenset({"read", "edit", "full"})


@dataclass(frozen=True)
class ResolvedPrincipal:
    """Uma linha de documento_acl (§6). Chave natural do pré-filtro."""
    principal_tipo: Literal["usuario", "grupo", "especial"]
    principal_ref: str


@dataclass(frozen=True)
class ResolvedDocument:
    """O que a ingestão persiste: doc + ACL resolvida + ABAC."""
    fonte: str
    fonte_ref: str
    setor: str
    principals: frozenset[ResolvedPrincipal]
    estudo_ref: str | None
    blinding: Literal["blinded", "unblinded"] | None
    sponsor_ref: str | None


def _principal_de_grant(g: Grant) -> ResolvedPrincipal | None:
    """Traduz UMA concessão crua em principal de leitura, ou None."""
    if g.nivel not in NIVEIS_DE_LEITURA:      # falha fechada
        return None
    return ResolvedPrincipal(g.principal_tipo, g.principal_ref)


def resolve(doc: SourceDocument) -> ResolvedDocument:
    """Resolve um documento da fonte para sua forma persistível.

    Idempotente e sem efeito colateral: mesma entrada -> mesma saída
    (necessário para reconciliação e reprocessamento — §4).
    """
    principals = frozenset(
        p for g in doc.grants
        if (p := _principal_de_grant(g)) is not None
    )
    # Invariante: doc sem principal é inacessível de propósito,
    # mas NUNCA por acidente de parsing. Quem chama decide se loga.

    return ResolvedDocument(
        fonte=doc.fonte,
        fonte_ref=doc.fonte_ref,
        setor=doc.setor,
        principals=principals,
        estudo_ref=doc.estudo_ref,
        blinding=doc.blinding,
        sponsor_ref=doc.sponsor_ref,
    )


def resolve_todos(docs: Iterable[SourceDocument]) -> list[ResolvedDocument]:
    return [resolve(d) for d in docs]