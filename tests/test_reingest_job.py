from datetime import datetime
from src.ingestion.reingest_job import (
    rodar, AprovacaoPendente, EventoReingest,
)

DIA = datetime(2026, 9, 30)


class LogFake:
    def __init__(self, pendentes):
        self._pendentes = list(pendentes)
        self.marcados: list[int] = []

    def aprovados_pendentes(self, dia):
        # simula reingerido_em IS NULL: some quem já foi marcado
        return [p for p in self._pendentes if p.auditoria_id not in self.marcados]

    def marcar_reingerido(self, auditoria_id, quando):
        self.marcados.append(auditoria_id)


class PublicadorFake:
    def __init__(self):
        self.publicados: list[EventoReingest] = []

    def publicar(self, evento):
        self.publicados.append(evento)


class PublicadorQuebrado:
    def publicar(self, evento):
        raise RuntimeError("barramento fora")


def test_emite_um_evento_por_aprovado():
    log = LogFake([AprovacaoPendente(1, 100), AprovacaoPendente(2, 200)])
    pub = PublicadorFake()
    r = rodar(DIA, log, pub)
    assert r.emitidos == 2
    assert {e.documento_id for e in pub.publicados} == {100, 200}


def test_marca_reingerido_apos_publicar():
    log = LogFake([AprovacaoPendente(1, 100)])
    rodar(DIA, log, PublicadorFake())
    assert 1 in log.marcados


def test_idempotente_segunda_rodada_nao_reemite():
    log = LogFake([AprovacaoPendente(1, 100)])
    pub = PublicadorFake()
    rodar(DIA, log, pub)
    rodar(DIA, log, pub)                 # marcado saiu da varredura
    assert len(pub.publicados) == 1

def test_falha_ao_publicar_nao_marca():
    log = LogFake([AprovacaoPendente(1, 100)])
    r = rodar(DIA, log, PublicadorQuebrado())
    assert r.falhos == 1
    assert log.marcados == []            # volta na próxima varredura (at-least-once)


def test_evento_carrega_origem_para_rastreio():
    log = LogFake([AprovacaoPendente(1, 100)])
    pub = PublicadorFake()
    rodar(DIA, log, pub)
    assert pub.publicados[0].origem_auditoria_id == 1