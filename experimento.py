"""Compara saldo e tempo com e sem semáforo.

Uso: python experimento.py --caixas 5 --operacoes 200 --delay 0 --repeticoes 10
"""

import argparse
import csv
import statistics
from threading import Semaphore, Thread
from time import perf_counter

from caixa import caixa, gerar_operacoes
from conta import Conta
from log import Extrato, habilitar_cores_no_windows, imprimir_auditoria

MODOS = {"sem_semaforo": lambda: None, "com_semaforo": lambda: Semaphore(1)}


def executar_simulacao_bancaria(inicial, grupos_de_operacoes, semaforo, delay, registrador=None):
    """Executa todas as threads uma vez e devolve (saldo_final, tempo)."""
    conta = Conta(inicial, semaforo, delay, registrador)
    threads = [
        Thread(target=caixa, args=(conta, operacoes), name=f"Caixa-{indice}")
        for indice, operacoes in enumerate(grupos_de_operacoes)
    ]
    tempo_inicial = perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    tempo_final = perf_counter()
    tempo_total = tempo_final - tempo_inicial
    return conta.saldo, tempo_total


def rodar_modo(nome, args, operacoes, esperado):
    """Repete o experimento R vezes para um modo e devolve linhas com os resultados."""
    resultados = []
    for repeticao in range(1, args.repeticoes + 1):
        extrato = Extrato() if args.verbose else None
        if extrato:
            print(f"\n=== {nome} | repetição {repeticao} ===")
        saldo, tempo = executar_simulacao_bancaria(
            args.inicial,
            operacoes,
            MODOS[nome](),
            args.delay,
            extrato.registrar if extrato else None,
        )
        if extrato:
            imprimir_auditoria(extrato.eventos)
        resultados.append(
            {
                "modo": nome,
                "repeticao": repeticao,
                "esperado": esperado,
                "saldo_final": saldo,
                "erro": esperado - saldo,
                "tempo_s": tempo,
            }
        )
    return resultados



def resumir(resultados):
    """Devolve estatísticas de um modo."""
    erros = [resultado["erro"] for resultado in resultados]
    tempos = [resultado["tempo_s"] for resultado in resultados]
    desvio = statistics.pstdev if len(resultados) > 1 else lambda _: 0.0
    return {
        "modo": resultados[0]["modo"],
        "errados": sum(1 for e in erros if e != 0),
        "total": len(resultados),
        "erro_medio": statistics.mean(erros),
        "erro_desvio": desvio(erros),
        "tempo_medio": statistics.mean(tempos),
        "tempo_desvio": desvio(tempos),
    }


def imprimir_tabela(resumos):
    cab = f"{'modo':<14}{'errados':>9}{'erro médio':>12}{'erro desv':>11}{'tempo (s)':>11}{'tempo desv':>12}"
    print(cab)
    print("-" * len(cab))
    for r in resumos:
        print(
            f"{r['modo']:<14}{r['errados']:>4}/{r['total']:<4}"
            f"{r['erro_medio']:>12.1f}{r['erro_desvio']:>11.1f}"
            f"{r['tempo_medio']:>11.4f}{r['tempo_desvio']:>12.4f}"
        )


def gravar_csv(caminho, linhas):
    with open(caminho, "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=linhas[0].keys())
        escritor.writeheader()
        escritor.writerows(linhas)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--caixas", type=int, default=5)
    p.add_argument("--operacoes", type=int, default=200)
    p.add_argument("--delay", type=float, default=0.0)
    p.add_argument("--repeticoes", type=int, default=10)
    p.add_argument("--inicial", type=int, default=1000)
    p.add_argument("--csv", help="grava as execuções individuais neste arquivo")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="imprime cada leitura/escrita; inconsistências em vermelho",
    )
    return p.parse_args()


def main():
    args = parse_args()
    habilitar_cores_no_windows()
    operacoes = gerar_operacoes(args.caixas, args.operacoes)
    saldo_esperado = args.inicial + sum(map(sum, operacoes))
    print(
        f"caixas={args.caixas} operacoes={args.operacoes} delay={args.delay}s "
        f"repeticoes={args.repeticoes} saldo esperado={saldo_esperado}\n"
    )
    todas_operacoes = []
    for nome in MODOS:
        todas_operacoes += rodar_modo(nome, args, operacoes, saldo_esperado)
    imprimir_tabela(
        [resumir([linha for linha in todas_operacoes if linha["modo"] == m]) for m in MODOS]
    )
    if args.csv:
        gravar_csv(args.csv, todas_operacoes)
        print(f"\nCSV gravado em {args.csv}")


if __name__ == "__main__":
    main()
