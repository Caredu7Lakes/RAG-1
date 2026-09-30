"""Job noturno de reingestão (§4, canal de conteúdo).

Roda no fim de cada dia. Varre auditoria_atualizacao por aprovados ainda
não reingeridos (reingerido_em IS NULL), emite UM evento de reingestão
por documento e marca como reingerido. NÃO reprocessa aqui — o consumidor
do evento (resolve_acl + chunker) faz o trabalho pesado, fora do caminho
do job.

Idempotente: marcar reingerido_em fecha a janela; rodar duas vezes no
mesmo dia não re-emite. Falha ao publicar NÃO marca — o doc volta na
próxima varredura (at-least-once).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AprovacaoPendente:
    """Linha de auditoria_atualizacao: aprovado, reingerido_em IS NULL."""
    auditoria_id: int
    documento_id: int


@dataclass(frozen=True)
class EventoReingest:
    documento_id: int
    origem_auditoria_id: int      # rastreabilidade: qual aprovação disparou


class LogReingest(Protocol):
    """Acesso ao log. Mock agora; Postgres (prepared statements) depois."""
    def aprovados_pendentes(self, dia: datetime) -> list[AprovacaoPendente]: ...
    def marcar_reingerido(self, auditoria_id: int, quando: datetime) -> None: ...


class PublicadorEvento(Protocol):
    """Barramento (Event Hubs). Publica o evento de reingestão."""
    def publicar(self, evento: EventoReingest) -> None: ...


@dataclass(frozen=True)
class ResultadoJob:
    emitidos: int
    falhos: int


def rodar(dia: datetime, log: LogReingest,
          publicador: PublicadorEvento) -> ResultadoJob:
    pendentes = log.aprovados_pendentes(dia)
    emitidos = 0
    falhos = 0
    for p in pendentes:
        evento = EventoReingest(
            documento_id=p.documento_id,
            origem_auditoria_id=p.auditoria_id,
        )
        try:
            publicador.publicar(evento)
        except Exception:
            falhos += 1                 # não marca: volta na próxima varredura
            continue
        log.marcar_reingerido(p.auditoria_id, dia)   # só marca após publicar
        emitidos += 1
    return ResultadoJob(emitidos=emitidos, falhos=falhos)