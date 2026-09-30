"""Relatorio de custo e latencia. Roda e imprime.

Custo: le PRECO_INPUT_USD_POR_1K do config. Editar o config -> novo custo aqui.
Latencia: cronometra o pre-filtro sobre N buscas, imprime p50/p95/p99.

Uso: python scripts\relatorio_custo_latencia.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PRECO_INPUT_USD_POR_1K, TOP_K_DEFAULT
from src.eval.custo import custo_contexto, custo_estimado_usd
from src.eval.latencia import Cronometro, ColetorLatencia
from src.query.membership import MembershipMock
from src.query.expand_principals import Usuario
from src.query.search import buscar
from src.query.search_backend import SearchBackendMock, IndexedChunk


def _cenario():
    chunks = [
        IndexedChunk(
            id=i, documento_id=i, ordem=0,
            conteudo=f"Conteudo do documento {i} sobre o estudo E1 " * 20,
            setor="regulado", principals=frozenset({("grupo", "clinica")}),
            estudo_ref="E1", blinding="blinded", sponsor_ref="SPON-A",
        )
        for i in range(1, 51)   # 50 chunks
    ]
    backend = SearchBackendMock(chunks)
    membership = MembershipMock({"u1": ["clinica"]})
    u = Usuario(id="u1", setor_id="regulado", sponsors_permitidos=("SPON-A",))
    return backend, membership, u


def main():
    backend, membership, u = _cenario()
    coletor = ColetorLatencia()
    N = 200

    # cronometra a busca (inclui o pre-filtro) N vezes
    ultimos_chunks = []
    for _ in range(N):
        with Cronometro() as cron:
            r = buscar(u, "estudo E1", membership, backend, k=TOP_K_DEFAULT)
        coletor.registrar(cron.ms)
        ultimos_chunks = r.chunks

    # custo do contexto recuperado (top-k)
    conteudos = [c.conteudo for c in ultimos_chunks]
    custo = custo_contexto(conteudos)
    usd = custo_estimado_usd(custo.tokens_total)

    print("=" * 48)
    print("RELATORIO DE CUSTO E LATENCIA")
    print("=" * 48)
    print(f"Amostras de busca...: {N}")
    print(f"Chunks no top-k.....: {custo.n_chunks} (k={TOP_K_DEFAULT})")
    print()
    print("-- CUSTO (contexto do top-k) --")
    print(f"Tokens totais.......: {custo.tokens_total}")
    print(f"Preco por 1k tokens.: US$ {PRECO_INPUT_USD_POR_1K}")
    print(f"Custo estimado......: US$ {usd:.6f}")
    print()
    print("-- LATENCIA (busca + pre-filtro, ms) --")
    print(f"p50.................: {coletor.p50:.4f} ms")
    print(f"p95.................: {coletor.p95:.4f} ms")
    print(f"p99.................: {coletor.p99:.4f} ms")
    print("=" * 48)


if __name__ == "__main__":
    main()