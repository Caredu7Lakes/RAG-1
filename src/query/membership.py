from typing import Protocol, Iterable


class MembershipProvider(Protocol):
    def grupos_de(self, usuario_id: str) -> Iterable[str]: ...


class MembershipMock:
    def __init__(self, mapa: dict[str, list[str]]):
        self._mapa = mapa

    def grupos_de(self, usuario_id: str) -> Iterable[str]:
        return self._mapa.get(usuario_id, [])