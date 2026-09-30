from src.eval.metrics import (
    recall_at_k, precision_at_k, reciprocal_rank, avaliar, CasoGolden,
)


def test_recall_completo():
    assert recall_at_k([1, 2, 3], frozenset({1, 2}), k=3) == 1.0


def test_recall_parcial():
    assert recall_at_k([1, 9, 9], frozenset({1, 2}), k=3) == 0.5


def test_recall_respeita_k():
    # relevante está na posição 3, mas k=2 não alcança
    assert recall_at_k([9, 9, 1], frozenset({1}), k=2) == 0.0


def test_recall_sem_relevantes_e_1():
    assert recall_at_k([1, 2], frozenset(), k=2) == 1.0


def test_precision_basica():
    assert precision_at_k([1, 9], frozenset({1}), k=2) == 0.5


def test_precision_topk_vazio_e_0():
    assert precision_at_k([], frozenset({1}), k=2) == 0.0


def test_mrr_primeiro_relevante_na_pos_2():
    assert reciprocal_rank([9, 1, 2], frozenset({1})) == 0.5


def test_mrr_nenhum_relevante():
    assert reciprocal_rank([9, 8], frozenset({1})) == 0.0


def test_avaliar_agrega_media():
    casos = [
        (CasoGolden("q1", frozenset({1})), [1, 9]),   # recall 1.0, prec@2 0.5, rr 1.0
        (CasoGolden("q2", frozenset({2})), [9, 2]),   # recall 1.0, prec@2 0.5, rr 0.5
    ]
    ag = avaliar(casos, k=2)
    assert ag.n_casos == 2
    assert ag.recall_at_k == 1.0
    assert ag.precision_at_k == 0.5
    assert ag.mrr == 0.75


def test_avaliar_vazio_nao_quebra():
    ag = avaliar([], k=5)
    assert ag.n_casos == 0