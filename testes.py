#!/usr/bin/env python3
"""Testes do simulador de rede de filas.

Os valores esperados de ``exemplo.yml``, ``exemplo_rnd.yml`` e ``t1.yml`` foram
obtidos executando o simulador de referência (simulator.jar, Módulo 3) com os
mesmos arquivos de modelo. O vetor do E1 é resolvido à mão no material (M4/E1).

Execução:
    python3 testes.py
"""

import unittest

import simulador as sim


TOLERANCIA = 1e-3


def estados(ambiente, qid):
    return dict(ambiente.filas[qid].estatistica)


class TestGeradorCongruenteLinear(unittest.TestCase):
    def test_faixa_e_reprodutibilidade(self):
        g1 = sim.GeradorCongruenteLinear(42)
        g2 = sim.GeradorCongruenteLinear(42)
        valores = [g1.next() for _ in range(1000)]
        self.assertTrue(all(0.0 <= v < 1.0 for v in valores))
        self.assertEqual(valores, [g2.next() for _ in range(1000)])

    def test_limite(self):
        g = sim.GeradorCongruenteLinear(7, limite=5)
        for _ in range(5):
            g.next()
        self.assertFalse(g.has_next())
        with self.assertRaises(sim.OutOfNumbers):
            g.next()


class TestVetorE1(unittest.TestCase):
    """Vetor determinístico do E1: G/G/1/3, randoms 0.4 0.2 0.7 0.5 0.1 0.8."""

    def test_estatisticas(self):
        parametros = sim.carrega_parametros("modelos/e1.yml")
        ambiente, _ = sim.simula(parametros)
        esperado = {0: 2.0, 1: 4.8, 2: 2.1}
        obtido = estados(ambiente, "F1")
        for estado, tempo in esperado.items():
            self.assertAlmostEqual(obtido[estado], tempo, delta=TOLERANCIA)
        self.assertAlmostEqual(ambiente.tempo_global(), 8.9, delta=TOLERANCIA)
        self.assertEqual(ambiente.filas["F1"].perdidos, 0)

    def test_conservacao(self):
        parametros = sim.carrega_parametros("modelos/e1.yml")
        ambiente, _ = sim.simula(parametros)
        aceitos, conservado = ambiente.verifica_conservacao()
        self.assertAlmostEqual(aceitos, conservado, delta=TOLERANCIA)


class TestExemploRnd(unittest.TestCase):
    """Rede de 4 filas do Módulo 3 com lista explícita de aleatórios."""

    GOLDEN = {
        "Q1": {0: 94.0088, 1: 33.6972},
        "Q2": {0: 55.0206, 1: 24.0396, 2: 20.6362, 3: 28.0096},
        "Q3": {0: 127.7060},
        "Q4": {0: 127.7060},
    }

    def test_estatisticas(self):
        parametros = sim.carrega_parametros("modelos/exemplo_rnd.yml")
        ambiente, simulacoes = sim.simula(parametros)
        self.assertEqual(simulacoes, 1)
        self.assertAlmostEqual(ambiente.tempo_global(), 127.7060, delta=TOLERANCIA)
        for qid, esperado in self.GOLDEN.items():
            obtido = estados(ambiente, qid)
            for estado, tempo in esperado.items():
                self.assertAlmostEqual(obtido[estado], tempo, delta=TOLERANCIA)


class TestExemploSementes(unittest.TestCase):
    """Média agregada de 5 sementes (1..5), como no relatório de referência."""

    GOLDEN = {
        "Q1": {0: 1556763.9510, 1: 984734.4270, 2: 27544.9674, 3: 231.3232},
        "Q2": {
            0: 25325.8646,
            1: 165968.3616,
            2: 434554.4680,
            3: 700389.0130,
            4: 790809.9556,
            5: 452227.0059,
        },
        "Q3": {
            0: 1636967.9845,
            1: 779468.0203,
            2: 140508.5906,
            3: 11822.0921,
            4: 507.7963,
            5: 0.1848,
        },
        "Q4": {0: 1931277.9789, 1: 576108.8657, 2: 59407.5978, 3: 2442.9579, 4: 37.2684},
    }
    PERDAS = {"Q1": 0, "Q2": 6244, "Q3": 0, "Q4": 0}

    def test_estatisticas(self):
        parametros = sim.carrega_parametros("modelos/exemplo.yml")
        ambiente, simulacoes = sim.simula(parametros)
        self.assertEqual(simulacoes, 5)
        self.assertAlmostEqual(ambiente.tempo_global(), 2569274.6687, delta=1e-2)
        for qid, esperado in self.GOLDEN.items():
            obtido = estados(ambiente, qid)
            for estado, tempo in esperado.items():
                self.assertAlmostEqual(obtido[estado], tempo, delta=1e-2)
            self.assertEqual(ambiente.filas[qid].perdidos, self.PERDAS[qid])


class TestModeloT1(unittest.TestCase):
    """Modelo do T1 (F1 G/G/1 infinita, F2 G/G/2/5, F3 G/G/2/10), semente 42."""

    GOLDEN = {
        "F1": {0: 20382.5718, 1: 26664.1092, 2: 3500.2678, 3: 137.4566, 4: 0.0381},
        "F2": {
            0: 12139.2869,
            1: 20973.8252,
            2: 13027.6448,
            3: 3872.7779,
            4: 620.2435,
            5: 50.6653,
        },
        "F3": {
            0: 7.0781,
            1: 2.0164,
            2: 6.6402,
            3: 6.4048,
            4: 5.9446,
            5: 6.2076,
            6: 7.0850,
            7: 56.0489,
            8: 2907.7363,
            9: 16137.1257,
            10: 31542.1560,
        },
    }
    PERDAS = {"F1": 0, "F2": 3, "F3": 11614}

    def test_estatisticas(self):
        parametros = sim.carrega_parametros("modelos/t1.yml")
        ambiente, _ = sim.simula(parametros)
        self.assertAlmostEqual(ambiente.tempo_global(), 50684.4435, delta=1e-2)
        for qid, esperado in self.GOLDEN.items():
            obtido = estados(ambiente, qid)
            for estado, tempo in esperado.items():
                self.assertAlmostEqual(obtido[estado], tempo, delta=1e-2)
            self.assertEqual(ambiente.filas[qid].perdidos, self.PERDAS[qid])

    def test_fila1_sem_perdas(self):
        parametros = sim.carrega_parametros("modelos/t1.yml")
        ambiente, _ = sim.simula(parametros)
        self.assertEqual(ambiente.filas["F1"].perdidos, 0)

    def test_conservacao(self):
        parametros = sim.carrega_parametros("modelos/t1.yml")
        ambiente, _ = sim.simula(parametros)
        aceitos, conservado = ambiente.verifica_conservacao()
        self.assertAlmostEqual(aceitos, conservado, delta=TOLERANCIA)

    def test_roteamento(self):
        parametros = sim.carrega_parametros("modelos/t1.yml")
        somas = {}
        for aresta in parametros.network:
            somas[aresta.source] = somas.get(aresta.source, 0.0) + aresta.probability
        self.assertAlmostEqual(somas["F1"], 1.0, delta=1e-9)
        self.assertAlmostEqual(somas["F2"], 0.8, delta=1e-9)
        self.assertAlmostEqual(somas["F3"], 0.7, delta=1e-9)
        self.assertEqual(sim.valida_roteamento(parametros), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
