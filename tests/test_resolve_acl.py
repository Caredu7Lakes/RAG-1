from pathlib import Path
from src.sources.base import SourceDocument, Grant
from src.sources.regulado_mock import ReguladoMock
from src.ingestion.resolve_acl import resolve, ResolvedPrincipal

FIXTURE = Path(__file__).parent / "fixtures" / "regulado.json"


def _doc(fonte_ref: str) -> SourceDocument:
    fonte = ReguladoMock(FIXTURE)
    return next(d for d in fonte.list_documents() if d.fonte_ref == fonte_ref)


# --- ACL: o que vira principal e o que não vira ---

def test_grant_de_leitura_vira_principal():
    r = resolve(_doc("E1-DOC-001"))
    assert ResolvedPrincipal("grupo", "funcao:bioestatistica") in r.principals


def test_nivel_invalido_some_falha_fechada():
    doc = SourceDocument(
        fonte="regulado", fonte_ref="X", tipo="pdf", setor="regulado", uri=None,
        grants=(Grant("grupo", "funcao:x", "read"),
                Grant("grupo", "funcao:y", "escrever_errado")),  # nível inválido
    )
    r = resolve(doc)
    refs = {p.principal_ref for p in r.principals}
    assert refs == {"funcao:x"}            # o inválido sumiu, o válido ficou


def test_grants_duplicados_deduplicam():
    doc = SourceDocument(
        fonte="regulado", fonte_ref="X", tipo="pdf", setor="regulado", uri=None,
        grants=(Grant("grupo", "funcao:x", "read"),
                Grant("grupo", "funcao:x", "edit")),   # mesmo grupo, 2x
    )
    assert len(resolve(doc).principals) == 1            # frozenset colapsa


# --- ABAC: resolve carrega, não decide ---

def test_abac_preservado_intacto():
    r = resolve(_doc("E1-DOC-001"))
    assert r.estudo_ref == "E1"
    assert r.blinding == "unblinded"
    assert r.sponsor_ref == "SPON-A"


def test_resolve_nao_aplica_regra_de_blinding():
    # resolve() NUNCA nega por blinding — isso é regra de consulta (§7).
    # Documento unblinded ainda emite seus principais normalmente.
    r = resolve(_doc("E1-DOC-001"))
    assert r.principals                                 # não veio vazio


# --- idempotência (necessária p/ reconciliação, §4) ---

def test_resolve_e_idempotente():
    doc = _doc("E2-DOC-001")
    assert resolve(doc) == resolve(doc)