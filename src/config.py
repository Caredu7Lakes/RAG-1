"""Constantes de configuração do retrieval.

Valores de tuning centralizados — não espalhar números mágicos.
Alterar aqui muda o trade-off recall x custo em todo o pipeline.
"""

# top-k: quantos chunks o retrieval retorna. Sobe recall, sobe custo/token.
TOP_K_DEFAULT = 10

# TTL do cache de membership, em segundos (§5). Piso de falha fechada.
MEMBERSHIP_TTL_S = 45.0

# Preço de input do seu contrato Azure, por 1.000 tokens. Editar quando mudar.
PRECO_INPUT_USD_POR_1K = 0.0025