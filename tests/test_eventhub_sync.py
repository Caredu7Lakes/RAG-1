import pytest
from src.acl.eventhub_sync import (
    EventoACL, TipoEvento, aplicar, aplicar_lote,
)


class IndiceFake:
    """Réplica mínima: doc_id -> set de principals."""
    def __init__(self):
        self.acl: dict[int, set[tuple[str, str]]] = {}

    def add_principal(self, documento_id, principal):
        self.acl.setdefault(documento_id, set()).add(principal)

    def remove_principal(self, documento_id, principal):
        self.acl.get(documento_id, set()).discard(principal)

    def remove_documento(self, documento_id):
        self.acl.pop(documento_id, None)


def test_concede_adiciona_principal():
    idx = IndiceFake()
    aplicar(EventoACL(TipoEvento.CONCEDE, 1, ("grupo", "clinica")), idx)
    assert ("grupo", "clinica") in idx.acl[1]


def test_revoga_remove_principal():
    idx = IndiceFake()
    idx.acl[1] = {("grupo", "clinica")}
    aplicar(EventoACL(TipoEvento.REVOGA, 1, ("grupo", "clinica")), idx)
    assert ("grupo", "clinica") not in idx.acl.get(1, set())


def test_remove_doc_apaga_tudo():
    idx = IndiceFake()
    idx.acl[1] = {("grupo", "clinica"), ("especial", "tenant:all")}
    aplicar(EventoACL(TipoEvento.REMOVE_DOC, 1), idx)
    assert 1 not in idx.acl


def test_revoga_sem_principal_falha_alto():
    idx = IndiceFake()
    with pytest.raises(ValueError):
        aplicar(EventoACL(TipoEvento.REVOGA, 1, None), idx)   # nunca silenciar revogação


def test_concede_sem_principal_e_ignorado():
    idx = IndiceFake()
    aplicar(EventoACL(TipoEvento.CONCEDE, 1, None), idx)      # não concede por acidente
    assert 1 not in idx.acl


def test_lote_prioriza_revogacao_sobre_concessao():
    idx = IndiceFake()
    idx.acl[1] = {("grupo", "clinica")}
    lote = [
        EventoACL(TipoEvento.CONCEDE, 1, ("grupo", "clinica")),
        EventoACL(TipoEvento.REVOGA, 1, ("grupo", "clinica")),
    ]
    aplicar_lote(lote, idx)
    # revogação vence mesmo vindo depois na lista original
    assert ("grupo", "clinica") not in idx.acl.get(1, set())


def test_idempotencia_revoga_duas_vezes():
    idx = IndiceFake()
    idx.acl[1] = {("grupo", "clinica")}
    ev = EventoACL(TipoEvento.REVOGA, 1, ("grupo", "clinica"))
    aplicar(ev, idx)
    aplicar(ev, idx)   # segunda vez não quebra
    assert ("grupo", "clinica") not in idx.acl.get(1, set())