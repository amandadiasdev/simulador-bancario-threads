"""Conta bancária compartilhada entre vários caixas (threads)."""

import time


def _sem_registro(tipo, acesso, *info):
    """Registrador padrão: apenas executa o acesso à memória."""
    return acesso()


class Conta:
    """Saldo compartilhado. `semaforo=None` desliga a proteção.

    A conta não sabe se está sendo usada de forma segura: ela só lê e escreve.
    `registrador(tipo, acesso, *info)` executa o acesso e pode anotar o que
    aconteceu, como uma câmera apontada para o caderno. Quem descobre erros é
    o auditor, depois, olhando o extrato.
    """

    def __init__(self, saldo_inicial, semaforo=None, delay=0.0, registrador=None):
        self.saldo = saldo_inicial
        self._sem = semaforo
        self._delay = delay
        self._registrar = registrador or _sem_registro

    def _ler(self):
        return self.saldo

    def _escrever(self, novo):
        self.saldo = novo
        return novo

    def _aplicar(self, valor):
        lido = self._registrar("leu", self._ler)  # 1. lê
        time.sleep(self._delay)  # 2. cede a vez (força a corrida)
        novo = lido + valor  # 3. calcula
        self._registrar("escreveu", lambda: self._escrever(novo), lido, valor)  # 4.

    def _executar(self, operacao):
        if self._sem is None:
            operacao()
            return
        with self._sem:
            operacao()

    def depositar(self, valor):
        self._executar(lambda: self._aplicar(+valor))

    def sacar(self, valor):
        self._executar(lambda: self._aplicar(-valor))
