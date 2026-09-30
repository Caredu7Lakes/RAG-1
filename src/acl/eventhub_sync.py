"""Sincroniza a réplica de ACL do índice a partir de eventos (§4).

Risco nº1 do projeto: se a réplica atrasar, um doc revogado continua
recuperável. Mitigação: propagação POR EVENTO (não por TTL). Uma
revogação atualiza o metadado do índice em segundos.

Este módulo APLICA eventos a um índice mutável. Quem PRODUZ os eventos
(CDC do Postgres -> Event Hubs) é externo ao mock — o contrato abaixo é
o ponto de troca para o Event Hubs real.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class TipoEvento(Enum):
    CONCEDE = "concede"       # adiciona principal a um doc
    REVOGA = "revoga"         # remove principal de um doc
    REMOVE_DOC = "remove_doc" # doc deletado/despublicado


@dataclass(frozen=True)
class EventoACL:
    tipo: TipoEvento
    documento_id: int
    principal: tuple[str, str] | None = None   # (tipo, ref); None p/ REMOVE_DOC


class IndiceMutavel(Protocol):
    """A réplica de ACL no índice (Azure AI Search). Mock e real satisfazem."""
    def add_principal(self, documento_id: int, principal: tuple[str, str]) -> None: ...
    def remove_principal(self, documento_id: int, principal: tuple[str, str]) -> None: ...
    def remove_documento(self, documento_id: int) -> None: ...


def aplicar(evento: EventoACL, indice: IndiceMutavel) -> None:
    """Aplica UM evento à réplica. Idempotente por tipo.

    REVOGA e REMOVE_DOC são falha-fechada: na dúvida, retiram acesso.
    Um evento malformado de concessão é ignorado (nunca concede por
    acidente); um de revogação malformado NÃO é silenciado."""
    if evento.tipo is TipoEvento.REMOVE_DOC:
        indice.remove_documento(evento.documento_id)
        return

    if evento.principal is None:
        if evento.tipo is TipoEvento.REVOGA:
            raise ValueError("REVOGA sem principal: não pode falhar em silêncio")
        return  # CONCEDE sem principal: ignora, nunca concede por acidente

    if evento.tipo is TipoEvento.CONCEDE:
        indice.add_principal(evento.documento_id, evento.principal)
    elif evento.tipo is TipoEvento.REVOGA:
        indice.remove_principal(evento.documento_id, evento.principal)


def aplicar_lote(eventos: list[EventoACL], indice: IndiceMutavel) -> None:
    """Prioridade: revogações e remoções vencem concessões no mesmo lote (§4).
    Não basta ordenar — uma concessão do mesmo (doc, principal) revogado
    no lote é descartada, senão re-adicionaria o que acabou de sair.
    Falha fechada: na dúvida, o acesso cai."""
    revogados: set[tuple[int, tuple[str, str]]] = {
        (e.documento_id, e.principal)
        for e in eventos
        if e.tipo is TipoEvento.REVOGA and e.principal is not None
    }
    docs_removidos: set[int] = {
        e.documento_id for e in eventos if e.tipo is TipoEvento.REMOVE_DOC
    }

    prioridade = {TipoEvento.REMOVE_DOC: 0, TipoEvento.REVOGA: 0,
                  TipoEvento.CONCEDE: 1}
    for e in sorted(eventos, key=lambda e: prioridade[e.tipo]):
        if e.tipo is TipoEvento.CONCEDE:
            if e.documento_id in docs_removidos:
                continue                                  # doc saiu: não concede
            if (e.documento_id, e.principal) in revogados:
                continue                                  # principal revogado no lote: vence
        aplicar(e, indice)