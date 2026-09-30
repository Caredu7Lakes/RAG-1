"""Cache de membership com TTL curto + invalidação por evento (§5).

Decorator sobre qualquer MembershipProvider (mock, Entra ID). Não toca
em expand_principals — só embrulha o provider.

Duas defesas contra membership obsoleta:
  - TTL curto (30–60s): teto de quanto uma entrada pode ficar velha.
  - Invalidação por evento: quem sai de um grupo é despejado do cache
    na hora, sem esperar o TTL. Revogação em segundos, não no próximo TTL.

Relógio injetável (agora) para o TTL ser testável sem sleep real.
"""
import time
from dataclasses import dataclass
from typing import Callable, Iterable
from .membership import MembershipProvider
from src.config import MEMBERSHIP_TTL_S


@dataclass
class _Entrada:
    grupos: tuple[str, ...]
    expira_em: float


class MembershipCache:
    """Envolve um provider. TTL + invalidação explícita por usuário."""

    def __init__(self, provider: MembershipProvider, ttl_s: float = MEMBERSHIP_TTL_S,
                 agora: Callable[[], float] = time.monotonic):
        self._provider = provider
        self._ttl_s = ttl_s
        self._agora = agora
        self._cache: dict[str, _Entrada] = {}

    def grupos_de(self, usuario_id: str) -> Iterable[str]:
        agora = self._agora()
        entrada = self._cache.get(usuario_id)
        if entrada is not None and agora < entrada.expira_em:
            return entrada.grupos                       # hit fresco

        grupos = tuple(self._provider.grupos_de(usuario_id))  # miss/expirado
        self._cache[usuario_id] = _Entrada(grupos, agora + self._ttl_s)
        return grupos

    def invalidar(self, usuario_id: str) -> None:
        """Despeja um usuário do cache (evento de mudança de grupo).
        Próxima consulta vai à fonte, sem esperar o TTL."""
        self._cache.pop(usuario_id, None)

    def invalidar_tudo(self) -> None:
        """Reset total (ex.: reconfiguração de grupos em massa)."""
        self._cache.clear()