"""Caixa eletrônico: função alvo de cada thread."""

import random


def caixa(conta, operacoes):
    """Aplica a lista de operações na conta (positivo deposita, negativo saca)."""
    for valor in operacoes:
        if valor >= 0:
            conta.depositar(valor)
        else:
            conta.sacar(-valor)


def gerar_operacoes(n_caixas, n_operacoes, valor=10, semente=42):
    """Gera uma lista fixa de operações por caixa, com semente fixa."""
    gerador = random.Random(semente)
    return [
        [gerador.choice((valor, -valor)) for _ in range(n_operacoes)]
        for _ in range(n_caixas)
    ]
