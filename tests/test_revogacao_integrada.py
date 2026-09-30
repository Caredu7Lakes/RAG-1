"""Loop fechado: revogação por evento -> busca seguinte não retorna (§4).

Este é o critério de aceite do 'risco nº1': um doc revogado deixa de ser
recuperável em segundos, sem reindex. Aqui, sem TTL: o evento atualiza a
ACL do backend e a próxima busca já reflete.
"""
from src.query.membership import MembershipMock
from src.query.expand_principals import Usuario
from src.query.search import buscar
from src.query.search_backend import SearchBackendMock, IndexedChunk
from src.acl.eventhub_sync import EventoACL, TipoEvento, aplicar


def _cenario():
    chunks = [
        IndexedChunk(
            id=1, documento_id=1, ordem=0, conteudo="dados do estudo E1",
            setor="regulado", principals=frozenset({("grupo", "clinica")}),
            estudo_ref="E1", blinding="blinded", sponsor_ref="SPON-A",
        ),
    ]
    backend = SearchBackendMock(chunks)
    membership = MembershipMock({"u1": ["clinica"]})
    u = Usuario(id="u1", setor_id="regulado", sponsors_permitidos=("SPON-A",))
    return backend, membership, u


def test_revogacao_torna_doc_invisivel_na_proxima_busca():
    backend, membership, u = _cenario()

    # antes: visível
    antes = {c.id for c in buscar(u, "dados", membership, backend).chunks}
    assert 1 in antes

    # evento de revogação do grupo clinica sobre o doc 1
    aplicar(EventoACL(TipoEvento.REVOGA, 1, ("grupo", "clinica")), backend)

    # depois: invisível, sem reindex
    depois = {c.id for c in buscar(u, "dados", membership, backend).chunks}
    assert 1 not in depois


def test_remove_doc_tira_de_todos():
    backend, membership, u = _cenario()
    aplicar(EventoACL(TipoEvento.REMOVE_DOC, 1), backend)
    assert buscar(u, "dados", membership, backend).chunks == []


def test_concessao_por_evento_torna_visivel():
    backend, membership, u = _cenario()
    # usuário de outro grupo, sem acesso inicial
    membership2 = MembershipMock({"u2": ["auditoria"]})
    u2 = Usuario(id="u2", setor_id="regulado", sponsors_permitidos=("SPON-A",))
    assert buscar(u2, "dados", membership2, backend).chunks == []

    aplicar(EventoACL(TipoEvento.CONCEDE, 1, ("grupo", "auditoria")), backend)
    assert 1 in {c.id for c in buscar(u2, "dados", membership2, backend).chunks}