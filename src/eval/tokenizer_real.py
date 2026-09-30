"""Contador de tokens real (tiktoken) para custo em USD absoluto.
So outra funcao contar injetada em custo_contexto; custo.py nao muda.
Encoding e POR MODELO; encoding_for_model resolve. Use o nome do MODELO
base do Azure OpenAI (ex.: gpt-4o), nao o nome do deployment.
"""
import tiktoken


def contador_para(modelo: str):
    enc = tiktoken.encoding_for_model(modelo)

    def contar(texto: str) -> int:
        return len(enc.encode(texto)) if texto else 0

    return contar
