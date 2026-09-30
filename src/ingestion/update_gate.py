"""Gate de atualização de documento (§ nova regra).

Fluxo: propor -> validar padrão -> aprovação humana -> aplicar + logar.
Regras:
  - Validação de padrão reprova ANTES da revisão humana (não gasta
    revisor com lixo).
  - Aprovação humana é obrigatória: nada atualiza sozinho.
  - Segregação de função: quem propõe NÃO pode aprovar a própria
    atualização (controle de qualidade real, não teatro).
  - Todo desfecho é logado: quem propôs, quem aprovou/rejeitou, por quê.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from .validators import DocumentoProposto, ValidadorPadrao


class Desfecho(Enum):
    REJEITADO_PADRAO = "rejeitado_padrao"     # falhou na validação automática
    PENDENTE = "pendente"                       # passou; aguarda humano
    APROVADO = "aprovado"                       # humano aprovou; aplicado
    REJEITADO_HUMANO = "rejeitado_humano"       # humano recusou


@dataclass(frozen=True)
class RegistroAuditoria:
    documento_id: int
    proposto_por: str
    aprovado_por: str | None
    desfecho: Desfecho
    motivo: str


class AuditLog(Protocol):
    """Log de atualização (tabela auditoria_atualizacao — a confirmar).
    Mock em memória agora; Postgres depois."""
    def registrar(self, r: RegistroAuditoria) -> None: ...


@dataclass(frozen=True)
class Pendente:
    doc: DocumentoProposto


def propor(doc: DocumentoProposto, validador: ValidadorPadrao,
           log: AuditLog) -> Pendente | None:
    """Valida o padrão. Passou -> Pendente (aguarda humano). Falhou ->
    loga rejeição e retorna None (nunca chega ao revisor)."""
    resultado = validador.validar(doc)
    if not resultado.ok:
        log.registrar(RegistroAuditoria(
            documento_id=doc.documento_id, proposto_por=doc.proposto_por,
            aprovado_por=None, desfecho=Desfecho.REJEITADO_PADRAO,
            motivo="; ".join(resultado.motivos),
        ))
        return None
    return Pendente(doc)


def aprovar(pendente: Pendente, aprovador_id: str, log: AuditLog) -> RegistroAuditoria:
    """Gate humano. Segregação de função: aprovador != propositor.
    Retorna o registro APROVADO — o disparo do evento de ingestão é
    responsabilidade de quem chama (a partir deste registro)."""
    doc = pendente.doc
    if aprovador_id == doc.proposto_por:
        raise ValueError("segregacao de funcao: quem propoe nao aprova")

    reg = RegistroAuditoria(
        documento_id=doc.documento_id, proposto_por=doc.proposto_por,
        aprovado_por=aprovador_id, desfecho=Desfecho.APROVADO,
        motivo="aprovado",
    )
    log.registrar(reg)
    return reg


def rejeitar(pendente: Pendente, revisor_id: str, motivo: str,
             log: AuditLog) -> RegistroAuditoria:
    """Humano recusa uma proposta que passou no padrão."""
    doc = pendente.doc
    reg = RegistroAuditoria(
        documento_id=doc.documento_id, proposto_por=doc.proposto_por,
        aprovado_por=revisor_id, desfecho=Desfecho.REJEITADO_HUMANO,
        motivo=motivo,
    )
    log.registrar(reg)
    return reg