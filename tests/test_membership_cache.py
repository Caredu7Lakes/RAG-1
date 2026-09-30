from src.query.membership import MembershipMock
from src.query.membership_cache import MembershipCache


class RelogioFake:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def avancar(self, s):
        self.t += s


class ProviderContado:
    """Conta quantas vezes a fonte real foi chamada."""
    def __init__(self, mapa):
        self._mock = MembershipMock(mapa)
        self.chamadas = 0

    def grupos_de(self, usuario_id):
        self.chamadas += 1
        return self._mock.grupos_de(usuario_id)


def test_hit_nao_chama_a_fonte_duas_vezes():
    prov = ProviderContado({"u1": ["clinica"]})
    rel = RelogioFake()
    cache = MembershipCache(prov, ttl_s=45, agora=rel)

    list(cache.grupos_de("u1"))
    list(cache.grupos_de("u1"))         # dentro do TTL: hit
    assert prov.chamadas == 1


def test_expira_apos_ttl():
    prov = ProviderContado({"u1": ["clinica"]})
    rel = RelogioFake()
    cache = MembershipCache(prov, ttl_s=45, agora=rel)

    list(cache.grupos_de("u1"))
    rel.avancar(46)                     # passou do TTL
    list(cache.grupos_de("u1"))         # miss: refaz
    assert prov.chamadas == 2


def test_invalidacao_por_evento_ignora_ttl():
    prov = ProviderContado({"u1": ["clinica"]})
    rel = RelogioFake()
    cache = MembershipCache(prov, ttl_s=45, agora=rel)

    list(cache.grupos_de("u1"))
    cache.invalidar("u1")               # evento: saiu de um grupo
    list(cache.grupos_de("u1"))         # vai à fonte mesmo dentro do TTL
    assert prov.chamadas == 2


def test_reflete_mudanca_apos_invalidar():
    prov = ProviderContado({"u1": ["clinica", "bioestatistica"]})
    rel = RelogioFake()
    cache = MembershipCache(prov, ttl_s=45, agora=rel)

    assert set(cache.grupos_de("u1")) == {"clinica", "bioestatistica"}
    # usuário perde um grupo na fonte
    prov._mock._mapa["u1"] = ["clinica"]
    cache.invalidar("u1")
    assert set(cache.grupos_de("u1")) == {"clinica"}   # revogação refletida


def test_cache_por_usuario_nao_vaza_entre_usuarios():
    prov = ProviderContado({"u1": ["clinica"], "u2": ["auditoria"]})
    rel = RelogioFake()
    cache = MembershipCache(prov, ttl_s=45, agora=rel)

    assert set(cache.grupos_de("u1")) == {"clinica"}
    assert set(cache.grupos_de("u2")) == {"auditoria"}
    cache.invalidar("u1")               # invalidar u1 não afeta u2
    list(cache.grupos_de("u2"))
    assert prov.chamadas == 2           # u1 e u2, uma vez cada; u2 não refez