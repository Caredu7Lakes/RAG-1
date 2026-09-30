"""Contrato do contador real (tiktoken). NÃO trava contagem exata —
o número muda entre versões da lib e valida-se contra a fatura, não em CI.
Testa só o contrato que custo_contexto espera de qualquer `contar`.

Requer tiktoken instalado; pula se ausente (CI sem a dependência).
"""
import pytest

tiktoken = pytest.importorskip("tiktoken")   # skip limpo se não instalado

from src.eval.tokenizer_real import contador_para
from src.eval.custo import custo_contexto


def test_retorna_int_nao_negativo():
    contar = contador_para("gpt-4o")
    assert isinstance(contar("texto qualquer"), int)
    assert contar("texto qualquer") > 0


def test_vazio_conta_zero():
    contar = contador_para("gpt-4o")
    assert contar("") == 0


def test_texto_maior_conta_mais():
    contar = contador_para("gpt-4o")
    assert contar("a" * 1000) > contar("a" * 10)


def test_encaixa_em_custo_contexto():
    # o contrato que importa: serve como `contar` injetado, sem mudar custo.py
    contar = contador_para("gpt-4o")
    c = custo_contexto(["primeiro chunk", "segundo chunk maior aqui"], contar=contar)
    assert c.n_chunks == 2
    assert c.tokens_total == sum(c.tokens_por_chunk)
    assert all(t > 0 for t in c.tokens_por_chunk)