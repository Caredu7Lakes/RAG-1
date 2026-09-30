import pytest
from src.ingestion.validators import PadraoBasico, DocumentoProposto
from src.ingestion.update_gate import (
    propor, aprovar, rejeitar, Desfecho, RegistroAuditoria,
)


class LogFake:
    def __init__(self):
        self.registros: list[RegistroAuditoria] = []

    def registrar(self, r):
        self.registros.append(r)


VALIDADOR = PadraoBasico()


def _doc_ok(**kw):
    base = dict(
        documento_id=1, conteudo="Conteudo valido e longo o suficiente.",
        setor="geral", proposto_por="alice", grants_count=1,
    )
    base.update(kw)
    return DocumentoProposto(**base)


# --- validação de padrão ---

def test_doc_curto_e_rejeitado_no_padrao():
    log = LogFake()
    r = propor(_doc_ok(conteudo="curto"), VALIDADOR, log)
    assert r is None
    assert log.registros[0].desfecho is Desfecho.REJEITADO_PADRAO


def test_regulado_sem_abac_e_rejeitado():
    log = LogFake()
    doc = _doc_ok(setor="regulado", estudo_ref=None, blinding=None)
    assert propor(doc, VALIDADOR, log) is None
    motivo = log.registros[0].motivo
    assert "estudo_ref" in motivo and "blinding" in motivo


def test_doc_sem_grant_e_rejeitado():
    log = LogFake()
    assert propor(_doc_ok(grants_count=0), VALIDADOR, log) is None


def test_doc_valido_fica_pendente_sem_logar_ainda():
    log = LogFake()
    p = propor(_doc_ok(), VALIDADOR, log)
    assert p is not None
    assert log.registros == []      # só loga em desfecho final


# --- gate humano ---

def test_aprovacao_humana_loga_quem_aprovou():
    log = LogFake()
    p = propor(_doc_ok(proposto_por="alice"), VALIDADOR, log)
    reg = aprovar(p, aprovador_id="bob", log=log)
    assert reg.desfecho is Desfecho.APROVADO
    assert reg.proposto_por == "alice" and reg.aprovado_por == "bob"


def test_propositor_nao_pode_aprovar_o_proprio():
    log = LogFake()
    p = propor(_doc_ok(proposto_por="alice"), VALIDADOR, log)
    with pytest.raises(ValueError):
        aprovar(p, aprovador_id="alice", log=log)   # segregação de função


def test_rejeicao_humana_registra_motivo():
    log = LogFake()
    p = propor(_doc_ok(), VALIDADOR, log)
    reg = rejeitar(p, revisor_id="bob", motivo="fonte nao confiavel", log=log)
    assert reg.desfecho is Desfecho.REJEITADO_HUMANO
    assert reg.motivo == "fonte nao confiavel"