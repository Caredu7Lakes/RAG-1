"""Instrumentação de latência do pré-filtro.

Mede o tempo de PARTE da busca (o pré-filtro de ACL), não a busca inteira.
Relógio injetável para teste determinístico. Em produção, coletar p50/p95/p99
sobre muitas amostras — este módulo produz as amostras; a agregação é abaixo.
"""
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Cronometro:
    """Contexto que mede tempo decorrido em ms. Relógio injetável."""
    relogio: Callable[[], float] = time.perf_counter
    _inicio: float = 0.0
    ms: float = 0.0

    def __enter__(self):
        self._inicio = self.relogio()
        return self

    def __exit__(self, *exc):
        self.ms = (self.relogio() - self._inicio) * 1000
        return False


@dataclass
class ColetorLatencia:
    """Acumula amostras de latência e computa percentis."""
    amostras: list[float] = field(default_factory=list)

    def registrar(self, ms: float) -> None:
        self.amostras.append(ms)

    def percentil(self, p: float) -> float:
        """p em 0..100. Interpolação simples sobre amostras ordenadas."""
        if not self.amostras:
            return 0.0
        ordenado = sorted(self.amostras)
        if len(ordenado) == 1:
            return ordenado[0]
        idx = (p / 100) * (len(ordenado) - 1)
        baixo = int(idx)
        frac = idx - baixo
        if baixo + 1 >= len(ordenado):
            return ordenado[baixo]
        return ordenado[baixo] + frac * (ordenado[baixo + 1] - ordenado[baixo])

    @property
    def p50(self) -> float:
        return self.percentil(50)

    @property
    def p95(self) -> float:
        return self.percentil(95)

    @property
    def p99(self) -> float:
        return self.percentil(99)