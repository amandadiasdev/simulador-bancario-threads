"""Extrato colorido das operações e auditoria posterior de atualizações perdidas."""

import sys
from dataclasses import dataclass
from threading import Lock, current_thread

RESET, NEGRITO, FRACO = "\033[0m", "\033[1m", "\033[2m"
VERMELHO, VERDE, AMARELO = "\033[91m", "\033[92m", "\033[33m"
PALETA = ["\033[96m", "\033[93m", "\033[95m", "\033[94m", "\033[92m", "\033[97m"]


@dataclass
class Evento:
    seq: int
    caixa: str
    tipo: str  # "leu" ou "escreveu"
    lido: int
    valor: int = 0
    novo: int = 0


def cor(caixa):
    indice = int(caixa.split("-")[-1]) if "-" in caixa else 0
    return PALETA[indice % len(PALETA)]


class Extrato:
    """Registra cada leitura/escrita em ordem e imprime ao vivo."""

    def __init__(self):
        self.eventos = []
        self._trava = Lock()  # protege só o extrato, não a conta

    def registrar(self, tipo, acesso, *info):
        """Executa o acesso à memória e o anota no mesmo instante.

        A trava garante que a linha do extrato saia na ordem real em que a
        memória foi lida ou escrita. Ela não protege a conta: a corrida entre a
        leitura e a escrita continua existindo.
        """
        with self._trava:
            resultado = acesso()
            if tipo == "leu":
                lido, valor, novo = resultado, 0, 0
            else:
                (lido, valor), novo = info, resultado
            ev = Evento(
                len(self.eventos) + 1, current_thread().name, tipo, lido, valor, novo
            )
            self.eventos.append(ev)
            print(self._linha(ev), flush=True)
        return resultado

    @staticmethod
    def _linha(ev):
        prefixo = f"{FRACO}#{ev.seq:<3}{RESET} {cor(ev.caixa)}{ev.caixa:<9}{RESET}"
        if ev.tipo == "leu":
            return f"{prefixo} {FRACO}leu {ev.lido}{RESET}"
        return f"{prefixo} escreveu {ev.lido} {ev.valor:+} = {ev.novo}"


def auditar(eventos):
    """Encontra escritas baseadas em leituras que outro caixa tornou obsoletas.

    Regra: se entre a leitura de um caixa e a sua escrita houve uma escrita de
    outro caixa, essa outra escrita foi apagada (atualização perdida).
    Devolve tuplas (leitura, intrusas, escrita).
    """
    perdidas = []
    ultima_leitura = {}
    for ev in eventos:
        if ev.tipo == "leu":
            ultima_leitura[ev.caixa] = ev
            continue
        leitura = ultima_leitura[ev.caixa]
        intrusas = [
            e
            for e in eventos[leitura.seq : ev.seq - 1]
            if e.tipo == "escreveu" and e.caixa != ev.caixa
        ]
        if intrusas:
            perdidas.append((leitura, intrusas, ev))
    return perdidas


def _linha_auditoria(ev, tom, comentario):
    nome = f"{cor(ev.caixa)}{ev.caixa:<8}{RESET}"
    if ev.tipo == "leu":
        acao = f"leu {ev.lido}"
    else:
        acao = f"escreveu {ev.lido} {ev.valor:+} = {ev.novo}"
    return f"      {tom}#{ev.seq:<3}{RESET} {nome} {tom}{acao:<26}{RESET} {FRACO}{comentario}{RESET}"


def _bloco_conflito(leitura, intrusas, escrita):
    saldo_real = intrusas[-1].novo
    correto = saldo_real + escrita.valor
    linhas = [
        f"\n  {VERMELHO}{NEGRITO}Conflito: #{escrita.seq} ({escrita.caixa}) apagou "
        f"{len(intrusas)} escrita(s) de outro(s) caixa(s){RESET}",
        _linha_auditoria(leitura, FRACO, "← valor em que a escrita se baseou"),
    ]
    for e in intrusas:
        linhas.append(
            _linha_auditoria(e, AMARELO, "✗ apagada: aconteceu depois da leitura")
        )
    linhas.append(
        _linha_auditoria(
            escrita, VERMELHO, f"← usou {escrita.lido}, mas o saldo já era {saldo_real}"
        )
    )
    linhas.append(
        f"      {FRACO}→ se tivesse relido, escreveria {saldo_real} {escrita.valor:+} = "
        f"{correto}; efeito apagado: {saldo_real - leitura.lido:+}{RESET}"
    )
    return "\n".join(linhas)


def imprimir_auditoria(eventos):
    perdidas = auditar(eventos)
    if not perdidas:
        print(
            f"\n{VERDE}{NEGRITO}Auditoria:{RESET}{VERDE} nenhuma atualização perdida.{RESET}"
        )
        return
    print(
        f"\n{VERMELHO}{NEGRITO}Auditoria:{RESET}{VERMELHO} {len(perdidas)} conflito(s). "
        f"Legenda: cinza = leitura de origem, amarelo = escritas apagadas, "
        f"vermelho = escrita que apagou.{RESET}"
    )
    for conflito in perdidas:
        print(_bloco_conflito(*conflito))


def habilitar_cores_no_windows():
    if sys.platform == "win32":
        import os

        os.system("")
