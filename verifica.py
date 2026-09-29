# Verifica os resultados do simulador contra os valores obtidos no simulador
# de referencia (simulator.jar) do modulo 3.
#
# Uso: python3 verifica.py

import simulador


def estatisticas(caminho, fila):
    esc, _ = simulador.simula(caminho)
    return esc.filas[fila].estatistica


def perto(a, b, tol=0.01):
    return abs(a - b) <= tol


# vetor do E1: G/G/1/3 com os 6 numeros aleatorios do enunciado
fila = estatisticas('modelos/e1.yml', 'F1')
assert perto(fila[0], 2.0)
assert perto(fila[1], 4.8)
assert perto(fila[2], 2.1)
print('E1 ok')

# exemplo do modulo 3 com lista explicita de aleatorios
esc, n = simulador.simula('modelos/exemplo_rnd.yml')
assert n == 1
assert perto(esc.filas['Q1'].estatistica[0], 94.0088)
assert perto(esc.filas['Q2'].estatistica[3], 28.0096)
assert perto(esc.tempo_global(), 127.7060)
print('exemplo (rndnumbers) ok')

# exemplo do modulo 3 com 5 sementes
esc, n = simulador.simula('modelos/exemplo.yml')
assert n == 5
assert esc.filas['Q2'].perdidos == 6244
assert perto(esc.tempo_global(), 2569274.6687)
print('exemplo (seeds) ok')

# modelo do T1: semente 42 e 100.000 aleatorios
esc, n = simulador.simula('modelos/t1.yml')
assert esc.filas['F1'].perdidos == 0
assert esc.filas['F2'].perdidos == 3
assert esc.filas['F3'].perdidos == 11614
assert perto(esc.filas['F3'].estatistica[10], 31542.1560)
assert perto(esc.tempo_global(), 50684.4435)
print('T1 ok')

print('tudo certo')
