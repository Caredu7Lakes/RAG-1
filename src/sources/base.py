from dataclasses import dataclass
from typing import Protocol, Iterator, Literal

@dataclass(frozen=True)
class Grant:                       # concessão crua, como a API entrega
    principal_tipo: Literal["usuario", "grupo", "especial"]
    principal_ref: str             # id, ou 'tenant:all' / 'sector:<id>' / 'team:<id>'
    nivel: Literal["read", "edit", "full"]

@dataclass(frozen=True)
class SourceDocument:
    fonte: str
    fonte_ref: str
    tipo: str
    setor: str
    uri: str | None
    grants: tuple[Grant, ...]
    estudo_ref: str | None = None                       # ABAC — só no regulado
    blinding: Literal["blinded", "unblinded"] | None = None
    sponsor_ref: str | None = None
    conteudo: str = ""

class DocumentSource(Protocol):    # mock e API real satisfazem isto
    fonte: str
    def health(self) -> bool: ...
    def list_documents(self) -> Iterator[SourceDocument]: ...