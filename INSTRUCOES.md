# Instrucoes de uso

Simulador de rede de filas por eventos discretos, em Python 3. Le um arquivo
.yml no mesmo formato do simulador do modulo 3 e imprime, para cada fila, o
tempo e a probabilidade de cada estado, o numero de perdas e a populacao media,
alem do tempo global da simulacao.

## Requisitos

Python 3 e a biblioteca PyYAML:

    pip install pyyaml

## Como rodar

    python3 simulador.py modelos/t1.yml

Para salvar a saida em arquivo:

    python3 simulador.py modelos/t1.yml > resultados/t1.txt

Para conferir os resultados contra o simulador de referencia do modulo 3:

    python3 verifica.py

## Arquivos

- modelos/t1.yml: modelo do T1.
- modelos/e1.yml: vetor do E1 (G/G/1/3).
- modelos/exemplo.yml: exemplo de 4 filas do modulo 3, com sementes.
- modelos/exemplo_rnd.yml: o mesmo exemplo, com lista explicita de aleatorios.
- resultados/t1.txt: saida do modelo do T1.
- resultados/t1_referencia.txt e resultados/exemplo_referencia.txt: saidas do
  simulator.jar, usadas para comparar.

## Formato do .yml

O arquivo comeca com a linha de marcacao !PARAMETERS (exigida pelo simulador do
modulo 3; aqui ela e apenas ignorada) e tem os blocos abaixo.

arrivals: instante da primeira chegada externa de cada fila. So as filas
listadas aqui recebem clientes do exterior.

queues: dados de cada fila.

- servers: numero de atendentes.
- capacity: numero maximo de clientes no sistema (em atendimento mais em
  espera). Se nao for informado, a fila e infinita.
- minArrival e maxArrival: intervalo entre chegadas externas.
- minService e maxService: tempo de atendimento.

network: roteamento, com source, target e probability. A soma das
probabilidades de uma fila nao precisa dar 1: o que faltar sai da rede
(exterior). Um target que nao seja uma fila do modelo tambem conta como saida.

seeds e rndnumbersPerSeed: geram os aleatorios automaticamente, um conjunto por
semente, com rndnumbersPerSeed numeros cada. Se seeds for usado, rndnumbers e
ignorado.

rndnumbers: lista fixa de aleatorios entre 0 e 1, usada para testar.

Os parametros a, c e m do gerador podem ser trocados (padrao 25214903917, 11 e
2^48, os mesmos do simulador do modulo 3).

## Como o simulador funciona

Os eventos sao do tipo chegada e saida. Uma saida guarda o destino sorteado
quando o atendimento comecou; se esse destino for outra fila, o cliente entra
nela (passagem), senao sai da rede.

Ao iniciar um atendimento, o simulador sorteia primeiro o roteamento e depois o
tempo de atendimento. Na chegada externa, o intervalo ate a proxima chegada e
sorteado por ultimo. Os numeros vem de U(a,b) = a + (b-a)*x.

O estado de uma fila e o numero de clientes no sistema, de 0 ate a capacidade.
Uma chegada, externa ou por passagem, em fila cheia e perdida. A cada evento
todas as filas acumulam o tempo que passaram no estado atual, e a probabilidade
de um estado e o tempo nele dividido pelo tempo global.

A simulacao para quando os numeros aleatorios acabam.

## Saida

Para cada fila o relatorio mostra a notacao, as chegadas e o atendimento, o
numero de perdas, a populacao media e uma linha por estado com o tempo
acumulado e a probabilidade. No fim aparece o tempo global da simulacao.
