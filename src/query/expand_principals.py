"""Expande um usuário em seus principals de leitura (§5).

Espelho invertido de resolve_acl: aqui SIM expandimos grupos, porque
membership muda rápido — congelá-la na ingestão deixaria quem saiu de
um grupo com acesso até o próximo reindex. Query-time + cache de TTL
curto (§5) = revogação em segundos.

Saída = dois arrays alinhados (tipos[], refs[]) + blinded_em[],
exatamente os parâmetros $1/$2/$3 do prefiltro.sql.
"""
from dataclasses import dataclass
from .membership import MembershipProvider


@dataclass(frozen=True)
class Usuario:
    id: str
    setor_id: str
    blinded_em: tuple[str, ...] = ()          # estudos onde é blinded
    sponsors_permitidos: tuple[str, ...] = () # sponsors que pode acessar (regulado)


@dataclass(frozen=True)
class QueryContext:
    principal_tipos: tuple[str, ...]      # -> $1
    principal_refs: tuple[str, ...]       # -> $2
    blinded_em: tuple[str, ...]           # -> $3
    sponsors_permitidos: tuple[str, ...]  # -> filtro de sponsor


def expand(usuario: Usuario, membership: MembershipProvider) -> QueryContext:
    pares: list[tuple[str, str]] = [
        ("usuario", usuario.id),                       # ele mesmo
        ("especial", "tenant:all"),                    # todo autenticado do tenant
        ("especial", f"sector:{usuario.setor_id}"),    # todos do setor
    ]
    for g in membership.grupos_de(usuario.id):         # grupos Entra ID / nativos
        pares.append(("grupo", g))

    pares = list(dict.fromkeys(pares))                 # dedup preservando alinhamento
    return QueryContext(
        principal_tipos=tuple(t for t, _ in pares),
        principal_refs=tuple(r for _, r in pares),
        blinded_em=usuario.blinded_em,
        sponsors_permitidos=usuario.sponsors_permitidos,
    )