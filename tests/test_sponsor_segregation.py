"""Segregação por sponsor (§3) — dimensão independente da ACL.

Setores se falam e grupos podem ser compartilhados entre sponsors, então
a interseção de principals NÃO basta. sponsor_ref é barreira própria:
visível só se (ACL casa) E (sponsor permitido).
"""
from src.query.membership import MembershipMock
from src.query.expand_principals import Usuario
from src.query.search import buscar
from src.query.search_backend import SearchBackendMock, IndexedChunk

# Grupo COMPARTILHADO (bioestatistica atende A e B) concede os dois docs.
# Sem a regra de sponsor, o usuário de A veria o doc de B — o vazamento.
CHUNKS = [
    IndexedChunk(
        id=1, documento_id=1, ordem=0, conteudo="dados do estudo sponsor A",
        setor="regulado", principals=frozenset({("grupo", "bioestatistica")}),
        estudo_ref="EA", blinding="blinded", sponsor_ref="SPON-A",
    ),
    IndexedChunk(
        id=2, documento_id=2, ordem=0, conteudo="dados do estudo sponsor B",
        setor="regulado", principals=frozenset({("grupo", "bioestatistica")}),
        estudo_ref="EB", blinding="blinded", sponsor_ref="SPON-B",
    ),
    
]
BACKEND = SearchBackendMock(CHUNKS)
# Usuário no grupo compartilhado, mas só autorizado ao SPON-A.
MEMBERSHIP = MembershipMock({"u1": ["bioestatistica"]})


def test_ve_doc_do_sponsor_permitido():
    u = Usuario(id="u1", setor_id="regulado", sponsors_permitidos=("SPON-A",))
    ids = {c.id for c in buscar(u, "dados", MEMBERSHIP, BACKEND).chunks}
    assert 1 in ids


def test_nao_ve_doc_de_sponsor_nao_permitido_mesmo_com_acl():
    u = Usuario(id="u1", setor_id="regulado", sponsors_permitidos=("SPON-A",))
    ids = {c.id for c in buscar(u, "dados", MEMBERSHIP, BACKEND).chunks}
    assert 2 not in ids          # ACL casa (grupo compartilhado), sponsor barra


def test_usuario_com_dois_sponsors_ve_ambos():
    u = Usuario(id="u1", setor_id="regulado", sponsors_permitidos=("SPON-A", "SPON-B"))
    ids = {c.id for c in buscar(u, "dados", MEMBERSHIP, BACKEND).chunks}
    assert {1, 2} <= ids