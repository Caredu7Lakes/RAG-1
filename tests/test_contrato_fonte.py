from pathlib import Path
from src.sources.regulado_mock import ReguladoMock
from src.sources.base import SourceDocument, Grant

FIXTURE = Path(__file__).parent / "fixtures" / "regulado.json"

def _fonte():                       # troque por ReguladoAPI(...) quando existir
    return ReguladoMock(FIXTURE)

def test_health():
    assert _fonte().health() is True

def test_documentos_respeitam_o_contrato():
    docs = list(_fonte().list_documents())
    assert docs, "fonte não pode vir vazia"
    for d in docs:
        assert isinstance(d, SourceDocument)
        assert d.grants and all(isinstance(g, Grant) for g in d.grants)

def test_regulado_sempre_tem_abac():
    for d in _fonte().list_documents():
        assert d.estudo_ref and d.blinding in ("blinded", "unblinded")