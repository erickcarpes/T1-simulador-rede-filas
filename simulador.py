#!/usr/bin/env python3
# Simulador de rede de filas por eventos discretos (T1)
#
# Le um modelo .yml no mesmo formato do simulador do modulo 3 e imprime, para
# cada fila, o tempo acumulado e a probabilidade de cada estado, o numero de
# perdas e a populacao media, alem do tempo global da simulacao.
#
# Uso: python3 simulador.py modelos/t1.yml

import sys

import yaml


class AcabouAleatorios(Exception):
    pass


class GeradorCongruenteLinear:
    # gerador pelo metodo congruente linear: x = (a*x + c) mod m, U = x / m
    def __init__(self, semente, limite, a=25214903917, c=11, m=2 ** 48):
        self.a = a
        self.c = c
        self.m = m
        self.x = semente
        self.limite = limite
        self.usados = 0

    def tem_proximo(self):
        return self.usados < self.limite

    def proximo(self):
        if not self.tem_proximo():
            raise AcabouAleatorios()
        self.x = (self.a * self.x + self.c) % self.m
        self.usados += 1
        return self.x / self.m


class ListaAleatorios:
    # fonte de numeros a partir de uma lista fixa (opcao rndnumbers)
    def __init__(self, valores):
        self.valores = list(valores)
        self.i = 0

    def tem_proximo(self):
        return self.i < len(self.valores)

    def proximo(self):
        if not self.tem_proximo():
            raise AcabouAleatorios()
        valor = self.valores[self.i]
        self.i += 1
        return valor


class Evento:
    def __init__(self, tempo, tipo, fila, destino):
        self.tempo = tempo
        self.tipo = tipo
        self.fila = fila
        self.destino = destino


class Fila:
    def __init__(self, nome):
        self.nome = nome
        self.ambiente = None
        self.populacao = 0
        self.capacidade = -1
        self.servidores = -1
        self.chegada_min = -1.0
        self.chegada_max = -1.0
        self.saida_min = -1.0
        self.saida_max = -1.0
        self.destinos = []
        self.estatistica = {}
        self.perdidos = 0

    def adiciona_destino(self, destino, probabilidade):
        self.destinos.append((float(probabilidade), destino))
        self.destinos.sort(key=lambda par: par[0])

    def sorteia_destino(self):
        # devolve None quando o cliente sai da rede (probabilidade restante)
        if not self.destinos:
            return None
        if len(self.destinos) == 1 and self.destinos[0][0] >= 1.0:
            return self.destinos[0][1]
        r = self.ambiente.gerador.proximo()
        for probabilidade, destino in self.destinos:
            if r <= probabilidade:
                return destino
            r -= probabilidade
        return None

    def chegada(self, agenda_chegada):
        self.ambiente.acumula_tempo()
        if self.capacidade < 0 or self.populacao < self.capacidade:
            self.populacao += 1
            if self.populacao <= self.servidores:
                # sorteia primeiro o roteamento e depois o tempo de atendimento
                self.ambiente.agenda_saida(self, self.sorteia_destino())
        else:
            self.perdidos += 1
        if agenda_chegada:
            self.ambiente.agenda_chegada(self)

    def saida(self):
        self.ambiente.acumula_tempo()
        self.populacao -= 1
        if self.populacao >= self.servidores:
            self.ambiente.agenda_saida(self, self.sorteia_destino())

    def __str__(self):
        return self.nome


class Escalonador:
    def __init__(self):
        self.filas = {}
        self.eventos = []
        self.eventos_iniciais = []
        self.gerador = None
        self.tempo = 0.0
        self.ultimo_evento = 0.0
        self.tempo_acumulado = 0.0

    def adiciona_fila(self, nome):
        fila = Fila(nome)
        fila.ambiente = self
        self.filas[nome] = fila
        return fila

    def fila(self, nome):
        return self.filas[nome]

    def novo_evento(self, tempo, tipo, fila, destino):
        return Evento(tempo, tipo, fila, destino)

    def insere(self, evento):
        self.eventos.append(evento)
        self.eventos.sort(key=lambda e: e.tempo)

    def agenda_chegada_inicial(self, fila, instante):
        evento = self.novo_evento(self.tempo + instante, 'chegada', fila, None)
        self.eventos_iniciais.append(evento)
        self.insere(evento)

    def agenda_chegada(self, fila):
        u = self.gerador.proximo()
        intervalo = fila.chegada_min + (fila.chegada_max - fila.chegada_min) * u
        self.insere(self.novo_evento(self.tempo + intervalo, 'chegada', fila, None))

    def agenda_saida(self, fila, destino):
        u = self.gerador.proximo()
        intervalo = fila.saida_min + (fila.saida_max - fila.saida_min) * u
        self.insere(self.novo_evento(self.tempo + intervalo, 'saida', fila, destino))

    def acumula_tempo(self):
        # acumula, em todas as filas, o tempo decorrido no estado atual
        intervalo = self.tempo - self.ultimo_evento
        for fila in self.filas.values():
            fila.estatistica[fila.populacao] = (
                fila.estatistica.get(fila.populacao, 0.0) + intervalo
            )
        self.ultimo_evento = self.tempo

    def escalona(self):
        evento = self.eventos.pop(0)
        self.ultimo_evento = self.tempo
        self.tempo = evento.tempo
        if evento.tipo == 'chegada':
            evento.fila.chegada(True)
        else:
            evento.fila.saida()
            if evento.destino is not None:
                evento.destino.chegada(False)

    def reinicia(self):
        self.eventos = list(self.eventos_iniciais)
        self.tempo_acumulado += self.tempo
        self.tempo = 0.0
        self.ultimo_evento = 0.0
        for fila in self.filas.values():
            fila.populacao = 0

    def tempo_global(self):
        return self.tempo + self.tempo_acumulado


A = 25214903917
C = 11
M = 2 ** 48


def carrega_modelo(caminho):
    # ignora a linha de marcacao '!PARAMETERS' exigida pelo simulador do modulo 3
    with open(caminho, encoding='utf-8') as arquivo:
        linhas = [linha for linha in arquivo if linha.strip() != '!PARAMETERS']
    return yaml.safe_load(''.join(linhas)) or {}


def monta_escalonador(modelo):
    esc = Escalonador()
    for nome, config in (modelo.get('queues') or {}).items():
        config = config or {}
        fila = esc.adiciona_fila(nome)
        fila.capacidade = int(config.get('capacity', -1))
        fila.servidores = int(config.get('servers', -1))
        fila.chegada_min = float(config.get('minArrival', -1.0))
        fila.chegada_max = float(config.get('maxArrival', -1.0))
        fila.saida_min = float(config.get('minService', -1.0))
        fila.saida_max = float(config.get('maxService', -1.0))
    for aresta in (modelo.get('network') or []):
        # alvo que nao e uma fila do modelo representa a saida da rede
        if aresta['target'] not in esc.filas:
            continue
        origem = esc.fila(aresta['source'])
        origem.adiciona_destino(esc.fila(aresta['target']), aresta['probability'])
    for nome, instante in (modelo.get('arrivals') or {}).items():
        esc.agenda_chegada_inicial(esc.fila(nome), float(instante))
    return esc


def simula(caminho):
    modelo = carrega_modelo(caminho)
    esc = monta_escalonador(modelo)
    seeds = modelo.get('seeds') or []
    limite = int(modelo.get('rndnumbersPerSeed', 100000))
    a = int(modelo.get('a', A))
    c = int(modelo.get('c', C))
    m = int(modelo.get('m', M))
    n = len(seeds) if seeds else 1
    for i in range(n):
        if seeds:
            esc.gerador = GeradorCongruenteLinear(int(seeds[i]), limite, a, c, m)
        else:
            esc.gerador = ListaAleatorios(modelo.get('rndnumbers') or [])
        try:
            while esc.gerador.tem_proximo():
                esc.escalona()
        except AcabouAleatorios:
            pass
        esc.reinicia()
    return esc, n


def notacao(fila):
    if fila.capacidade < 0:
        return 'G/G/%d' % fila.servidores
    return 'G/G/%d/%d' % (fila.servidores, fila.capacidade)


def imprime_relatorio(esc, n):
    total = esc.tempo_global()
    numero = 0
    for fila in esc.filas.values():
        numero += 1
        print('Resultado da Fila %d: %s' % (numero, notacao(fila)), end='')
        if fila.chegada_min >= 0.0:
            print(', chegadas entre %s...%s' % (fila.chegada_min, fila.chegada_max), end='')
        print(', atendimento entre %s...%s' % (fila.saida_min, fila.saida_max))
        print('perdas: %d' % fila.perdidos)
        media = 0.0
        for estado, tempo in fila.estatistica.items():
            media += estado * tempo
        media = media / total if total else 0.0
        print('populacao media: %.4f' % media)
        print('estados:')
        for estado in sorted(fila.estatistica):
            tempo = fila.estatistica[estado]
            probabilidade = 100.0 * tempo / total if total else 0.0
            print('  %d: %.4f min (%.2f%%)' % (estado, tempo, probabilidade))
        print()
    print('tempo global da simulacao: %.4f min' % total)
    if n > 1:
        print('tempo medio por simulacao: %.4f min' % (total / n))


def roda():
    if len(sys.argv) < 2:
        print('uso: python3 simulador.py <arquivo.yml>')
        return
    esc, n = simula(sys.argv[1])
    imprime_relatorio(esc, n)


if __name__ == '__main__':
    roda()
