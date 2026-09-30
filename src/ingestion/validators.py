"""Padrão que um documento deve seguir para ser aceito (garante
qualidade futura dos chunks). Strategy: regra concreta agora, trocável.

Um doc que falha aqui NUNCA entra na ingestão — logo nunca vira chunk
ruim. Falha na origem é mais barata que chunk ruim em produção.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResultadoValidacao:
    ok: bool
    motivos: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentoProposto:
    documento_id: int
    conteudo: str
    setor: str
    proposto_por: str
    # ABAC (obrigatório no setor regulado)
    estudo_ref: str | None = None
    blinding: str | None = None
    grants_count: int = 0


class ValidadorPadrao(Protocol):
    def validar(self, doc: DocumentoProposto) -> ResultadoValidacao: ...


class PadraoBasico:
    """Regras mínimas de qualidade. Acumula TODOS os motivos de falha
    (não para no primeiro) — o revisor humano vê a lista inteira."""

    TAMANHO_MINIMO = 20   # chars; abaixo disso não gera chunk útil

    def validar(self, doc: DocumentoProposto) -> ResultadoValidacao:
        motivos: list[str] = []

        if len(doc.conteudo.strip()) < self.TAMANHO_MINIMO:
            motivos.append(f"conteudo abaixo de {self.TAMANHO_MINIMO} chars")

        if "\ufffd" in doc.conteudo:                 # replacement char = encoding quebrado
            motivos.append("conteudo com encoding invalido (U+FFFD)")

        if doc.grants_count == 0:
            motivos.append("documento sem nenhum grant (seria invisivel)")

        if doc.setor == "regulado":
            if not doc.estudo_ref:
                motivos.append("setor regulado exige estudo_ref")
            if doc.blinding not in ("blinded", "unblinded"):
                motivos.append("setor regulado exige blinding valido")

        return ResultadoValidacao(ok=not motivos, motivos=tuple(motivos))