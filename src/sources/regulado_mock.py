import json
from pathlib import Path
from .base import SourceDocument, Grant

class ReguladoMock:
    """Simula a API do repositório regulado via fixtures.
    Mesmo contrato (DocumentSource) da futura API real."""
    fonte = "regulado"

    def __init__(self, fixture: Path):
        self._fixture = fixture

    def health(self) -> bool:
        return self._fixture.exists()

    def list_documents(self):
        data = json.loads(self._fixture.read_text(encoding="utf-8"))
        for d in data["documentos"]:
            yield SourceDocument(
                fonte=self.fonte, fonte_ref=d["fonte_ref"], tipo=d["tipo"],
                setor=d["setor"], uri=d.get("uri"),
                grants=tuple(Grant(**g) for g in d["grants"]),
                estudo_ref=d.get("estudo_ref"), blinding=d.get("blinding"),
                sponsor_ref=d.get("sponsor_ref"), conteudo=d.get("conteudo", ""),
            )