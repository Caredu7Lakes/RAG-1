from src.ingestion.chunker import FixedSizeChunker, chunk_documento, Chunk


def test_texto_curto_vira_um_chunk():
    c = FixedSizeChunker(tamanho=100, overlap=20)
    assert c.split("texto pequeno") == ["texto pequeno"]


def test_texto_vazio_nao_gera_chunk():
    c = FixedSizeChunker(tamanho=100, overlap=20)
    assert c.split("   ") == []


def test_janela_desliza_com_overlap():
    c = FixedSizeChunker(tamanho=10, overlap=3)
    partes = c.split("abcdefghijklmnop")   # 16 chars
    assert len(partes) > 1
    # overlap: fim de um chunk reaparece no começo do próximo
    assert partes[0][-3:] == partes[1][:3]


def test_overlap_invalido_falha_cedo():
    import pytest
    with pytest.raises(ValueError):
        FixedSizeChunker(tamanho=10, overlap=10)


def test_ordem_estavel_e_sequencial():
    c = FixedSizeChunker(tamanho=10, overlap=2)
    chunks = chunk_documento(documento_id=1, texto="a" * 50, strategy=c)
    assert [k.ordem for k in chunks] == list(range(len(chunks)))
    assert all(isinstance(k, Chunk) for k in chunks)


def test_comprimento_injetavel():
    # mede por "palavras" em vez de chars — prova que a unidade é trocável
    por_palavra = lambda s: len(s.split())
    c = FixedSizeChunker(tamanho=3, overlap=1, comprimento=por_palavra)
    # a lógica de fatiamento ainda usa índice de char; o teste só garante
    # que a função é aceita e o texto curto (<=3 palavras) fica inteiro
    assert c.split("uma duas tres") == ["uma duas tres"]