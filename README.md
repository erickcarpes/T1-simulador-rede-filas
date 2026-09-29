# T1 - Simulador de rede de filas

Simulador de eventos discretos em Python para redes de filas com roteamento
variavel. Le o modelo de um arquivo .yml no mesmo formato do simulador do
modulo 3 e gera o relatorio pedido no T1: tempo e probabilidade de cada estado
das filas, numero de perdas e tempo global.

Modelo do T1: Fila 1 G/G/1 (capacidade infinita, chegadas 2..4, atendimento
1..2), Fila 2 G/G/2/5 (atendimento 4..6) e Fila 3 G/G/2/10 (atendimento 5..15),
com as probabilidades de roteamento do enunciado. Filas vazias no inicio, 1a
chegada em t = 2.0 e parada em 100.000 aleatorios.

    pip install pyyaml
    python3 simulador.py modelos/t1.yml

As instrucoes completas estao em INSTRUCOES.md e os resultados do T1 em
resultados/t1.txt.
