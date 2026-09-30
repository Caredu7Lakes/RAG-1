from src.eval.custo import (
    aprox_tokens, custo_contexto, custo_estimado_usd,
)


def test_aprox_tokens_quatro_chars():
    assert aprox_tokens("a" * 400) == 100


def test_aprox_tokens_vazio_e_zero():
    assert aprox_tokens("") == 0


def test_aprox_tokens_minimo_um():
    assert aprox_tokens("ab") == 1          # texto curto conta 1, não 0


def test_custo_soma_por_chunk():
    c = custo_contexto(["a" * 400, "b" * 800])
    assert c.n_chunks == 2
    assert c.tokens_por_chunk == (100, 200)
    assert c.tokens_total == 300


def test_contador_injetavel():
    # conta por palavra em vez de char — prova que é trocável
    por_palavra = lambda s: len(s.split())
    c = custo_contexto(["uma duas tres", "quatro cinco"], contar=por_palavra)
    assert c.tokens_total == 5


def test_k_maior_custa_mais():
    # mesmo corpus, top-3 vs top-1: mais chunks = mais token
    corpus = ["x" * 400] * 5
    top1 = custo_contexto(corpus[:1]).tokens_total
    top3 = custo_contexto(corpus[:3]).tokens_total
    assert top3 > top1                       # trade-off recall x custo


def test_custo_usd():
    # 1000 tokens a $0.002/1k = $0.002
    assert custo_estimado_usd(1000, usd_por_1k=0.002) == 0.002


def test_custo_usd_escala_linear():
    assert custo_estimado_usd(5000, usd_por_1k=0.01) == 0.05