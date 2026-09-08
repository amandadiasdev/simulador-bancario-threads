"""Bateria de experimentos: grava todas as execuções em um único CSV.

Uso: python bateria.py --saida ../resultados/resultados.csv
"""

import argparse
import contextlib
import csv
import os
import platform
import sys
from threading import Semaphore

from caixa import gerar_operacoes
from experimento import MODOS, resumir, rodar_uma_vez
from log import Extrato

# (nome, caixas, operacoes, delay, repeticoes, verbose)
CENARIOS = [
    ("A_base", 5, 200, 0.0, 20, False),
    ("B_tempo", 5, 200, 0.001, 10, False),
    ("C_minimo", 2, 100, 0.001, 10, False),
    ("D_escala", 20, 2000, 0.0, 5, False),
    ("E_verbose", 5, 200, 0.0, 10, True),
    ("F_controle_1_caixa", 1, 1000, 0.0, 10, False),
]
INICIAL = 1000


def executar_cenario(nome, caixas, operacoes, delay, repeticoes, verbose):
    ops = gerar_operacoes(caixas, operacoes)
    esperado = INICIAL + sum(map(sum, ops))
    linhas = []
    for modo in MODOS:
        for rep in range(1, repeticoes + 1):
            saldo, tempo = _rodar(ops, MODOS[modo](), delay, verbose)
            linhas.append(
                {
                    "cenario": nome,
                    "caixas": caixas,
                    "operacoes": operacoes,
                    "delay_s": delay,
                    "verbose": int(verbose),
                    "modo": modo,
                    "repeticao": rep,
                    "esperado": esperado,
                    "saldo_final": saldo,
                    "erro": esperado - saldo,
                    "tempo_s": round(tempo, 6),
                }
            )
    return linhas


def _rodar(ops, semaforo, delay, verbose):
    if not verbose:
        return rodar_uma_vez(INICIAL, ops, semaforo, delay)
    extrato = Extrato()
    with open(os.devnull, "w") as nulo, contextlib.redirect_stdout(nulo):
        return rodar_uma_vez(INICIAL, ops, semaforo, delay, extrato.registrar)


def imprimir_resumo(linhas):
    print(
        f"Python {platform.python_version()} | {platform.system()} {platform.machine()}\n"
    )
    cab = f"{'cenário':<20}{'modo':<14}{'errados':>9}{'erro médio':>12}{'tempo médio (s)':>17}"
    print(cab + "\n" + "-" * len(cab))
    for nome, *_ in CENARIOS:
        for modo in MODOS:
            grupo = [l for l in linhas if l["cenario"] == nome and l["modo"] == modo]
            r = resumir(grupo)
            print(
                f"{nome:<20}{modo:<14}{r['errados']:>4}/{r['total']:<4}"
                f"{r['erro_medio']:>12.1f}{r['tempo_medio']:>17.4f}"
            )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--saida", default="resultados.csv")
    args = p.parse_args()
    linhas = []
    for cenario in CENARIOS:
        print(f"executando {cenario[0]}...", file=sys.stderr)
        linhas += executar_cenario(*cenario)
    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    with open(args.saida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=linhas[0].keys())
        w.writeheader()
        w.writerows(linhas)
    imprimir_resumo(linhas)
    print(f"\nCSV: {args.saida} ({len(linhas)} execuções)")


if __name__ == "__main__":
    main()
