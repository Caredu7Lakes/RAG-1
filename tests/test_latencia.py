from src.eval.latencia import Cronometro, ColetorLatencia


class RelogioFake:
    def __init__(self, marcas):
        self._marcas = iter(marcas)

    def __call__(self):
        return next(self._marcas)


def test_cronometro_mede_decorrido_em_ms():
    rel = RelogioFake([1.0, 1.5])   # 0.5s = 500ms
    with Cronometro(relogio=rel) as c:
        pass
    assert c.ms == 500.0


def test_coletor_vazio_retorna_zero():
    assert ColetorLatencia().p50 == 0.0


def test_coletor_uma_amostra():
    col = ColetorLatencia()
    col.registrar(10.0)
    assert col.p50 == 10.0 and col.p99 == 10.0


def test_percentis_ordenam():
    col = ColetorLatencia()
    for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        col.registrar(v)
    assert col.p50 < col.p95 <= col.p99


def test_p95_de_cem_amostras():
    col = ColetorLatencia()
    for v in range(1, 101):        # 1..100
        col.registrar(float(v))
    assert 95 <= col.p95 <= 96     # ~95º valor