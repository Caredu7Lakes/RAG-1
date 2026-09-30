from src.query.membership import MembershipMock
from src.query.expand_principals import Usuario
from src.query.search import buscar
from src.query.search_backend import SearchBackendMock, IndexedChunk

# Chunks do setor regulado: todos com sponsor_ref (regra: sem sponsor nao sobe).
CHUNKS = [
    IndexedChunk(
        id=1, documento_id=1, ordem=0, conteudo="Protocolo blinded do estudo E1",
        setor="regulado", principals=frozenset({("grupo", "funcao:clinica")}),
        estudo_ref="E1", blinding="blinded", sponsor_ref="SPON-A",
    ),
    IndexedChunk(
        id=2, documento_id=2, ordem=0, conteudo="Randomizacao unblinded do estudo E1",
        setor="regulado", principals=frozenset({("grupo", "funcao:bioestatistica")}),
        estudo_ref="E1", blinding="unblinded", sponsor_ref="SPON-A",
    ),
    IndexedChunk(
        id=3, documento_id=3, ordem=0, conteudo="Comunicado geral do estudo E1",
        setor="regulado", principals=frozenset({("especial", "tenant:all")}),
        estudo_ref="E1", blinding="blinded", sponsor_ref="SPON-A",
    ),
]
BACKEND = SearchBackendMock(CHUNKS)
MEMBERSHIP = MembershipMock({"u_clinica": ["funcao:clinica"]})

# Usuario autorizado ao SPON-A (senao a regra de sponsor barra tudo).
def _u(**kw):
    base = dict(id="u_clinica", setor_id="regulado", sponsors_permitidos=("SPON-A",))
    base.update(kw)
    return Usuario(**base)


def test_recupera_o_que_tem_permissao():
    r = buscar(_u(), "estudo E1", MEMBERSHIP, BACKEND)
    ids = {c.id for c in r.chunks}
    assert 1 in ids            # tem o grupo clinica
    assert 3 in ids            # tenant:all pega todo autenticado


def test_nao_vaza_doc_de_outro_grupo():
    r = buscar(_u(), "estudo E1", MEMBERSHIP, BACKEND)
    ids = {c.id for c in r.chunks}
    assert 2 not in ids        # bioestatistica - intersecao vazia = invisivel


def test_blinded_nao_ve_unblinded():
    membership = MembershipMock({"u_bio": ["funcao:bioestatistica"]})
    u = _u(id="u_bio", blinded_em=("E1",))
    r = buscar(u, "estudo E1", membership, BACKEND)
    ids = {c.id for c in r.chunks}
    assert 2 not in ids        # ABAC barra apesar do principal casar


def test_usuario_sem_principal_nao_recupera_nada():
    r = buscar(_u(), "termo_inexistente", MEMBERSHIP, BACKEND)
    assert r.chunks == []      # nada casa a consulta, sem erro
