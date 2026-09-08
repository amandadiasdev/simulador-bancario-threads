# Conta bancária com múltiplos caixas

Vários caixas eletrônicos (threads) operam a mesma conta (variável compartilhada). Cada operação lê o saldo, espera um instante e escreve o novo valor. Sem exclusão mútua, uma escrita apaga a outra. Com um `Semaphore(1)` ao redor da operação, o saldo final fica correto.

## Arquivos

- `conta.py` — classe `Conta` com `depositar` e `sacar`. Recebe um semáforo opcional; `None` desliga a proteção.  
- `caixa.py` — função alvo das threads e gerador de operações com semente fixa.  
- `experimento.py` — roda os dois modos, repete R vezes, mede erro e tempo.  
- `log.py` — impressão colorida e thread-safe usada pelo modo `--verbose`.  
- `bateria.py` — roda os seis cenários do relatório e grava um único CSV em `../resultados/resultados.csv`. Análise em `../resultados/RESULTADOS.md`.

## Como rodar

Para medir tempo com a região crítica visível:

```shell
python3 experimento.py --delay 0.001 --repeticoes 3 --csv resultados.csv
```

## Modo verboso (somente para entender a corrida)

```shell
python3 experimento.py --caixas 3 --operacoes 3 --repeticoes 1 --delay 0.001 --verbose
```

Cada caixa recebe uma cor. O extrato mostra, numerado e na ordem real em que a memória foi tocada, cada `leu` (cinza) e cada `escreveu` (cor do caixa). A conta não sabe se algo deu errado: ela só lê e escreve.

Quem descobre o problema é a **auditoria**, que roda depois, lendo o extrato como um auditor lê o caderno no fim do dia. A regra é simples: se entre a leitura de um caixa e a sua escrita houve uma escrita de outro caixa, a escrita do outro foi apagada. Cada conflito vira um bloco com a leitura de origem (cinza), as escritas apagadas (amarelo) e a escrita que apagou (vermelho), mais o valor que teria sido escrito se o caixa tivesse relido o saldo. Com semáforo a auditoria não encontra nada. Use `--delay 0.001` no modo verboso: com poucas operações e `delay=0` as threads costumam terminar uma antes de a outra começar, e a corrida não aparece.

Como a ordem é garantida: o registro e o acesso à memória acontecem dentro da mesma trava do extrato, então a linha impressa corresponde ao instante real da leitura ou da escrita. Essa trava não envolve o `sleep`, portanto a corrida continua existindo; ela só impede que a impressão minta sobre a ordem. Sem `--verbose` nenhuma trava extra é usada, e as medidas de tempo da tabela não são afetadas.

## Por que o `sleep` entre ler e escrever

O GIL do Python protege cada instrução do interpretador, mas "ler, calcular, escrever" são três instruções. O `time.sleep(delay)` no meio libera o GIL e força a troca de thread exatamente onde a preempção faria estrago em C ou entre processos. Com `delay=0` a corrida já aparece de forma confiável.

## Resultados obtidos (Python 3.14.6)

`caixas=5 operacoes=200 repeticoes=10 delay=0`, saldo esperado 720:

| modo | errados | erro médio | tempo médio (s) |
| :---- | :---- | :---- | :---- |
| sem\_semaforo | 10/10 | \-280.0 | 0.0028 |
| com\_semaforo | 0/10 | 0.0 | 0.0033 |

`delay=0.001 repeticoes=3`:

| modo | errados | erro médio | tempo médio (s) |
| :---- | :---- | :---- | :---- |
| sem\_semaforo | 3/3 | \-286.7 | 0.26 |
| com\_semaforo | 0/3 | 0.0 | 1.41 |

Com semáforo o tempo cresce cerca de 5x porque as 5 threads passam a executar a região crítica uma por vez (5 × 200 × 1 ms ≈ 1 s de espera serializada, mais a sobrecarga do `sleep`). Sem semáforo as esperas se sobrepõem (200 × 1 ms ≈ 0,2 s), mas o saldo sai errado em todas as execuções.

## Com semáforo pode ficar mais rápido?

Sem `--verbose` e com `delay > 0`, não: a região crítica é serializada e o tempo cresce com o número de caixas (medido: 0,26 s contra 1,29 s com `delay=0.001`). Com `delay=0` os tempos ficam próximos (0,0027 s contra 0,0032 s).

Com `--verbose` e `delay=0`, sim, e isso não é erro. Medido: 0,017 s sem semáforo contra 0,011 s com semáforo. Dois motivos:

1. No modo verboso, cada leitura e escrita passa pela trava do extrato e por um `print`. Sem semáforo, cinco threads disputam essa trava o tempo todo e o sistema fica trocando de thread a cada evento. Com semáforo só uma thread está ativa, então a trava do extrato nunca é disputada.  
2. O `time.sleep(0)` cede a vez a quem estiver pronto. Sem semáforo há sempre outra thread pronta, e cada ceder vira uma troca de contexto. Com semáforo as outras estão bloqueadas esperando a permissão, então o `sleep(0)` volta na hora.

Ou seja: o custo do semáforo é esperar na fila enquanto alguém usa a região crítica. Quando a região crítica é quase instantânea, esse custo é menor do que o custo da bagunça de cinco threads se atropelando. Assim que a região crítica demora (`delay > 0`), a fila passa a dominar e o semáforo fica mais lento. Para medir o custo do semáforo, use a tabela sem `--verbose`.  
