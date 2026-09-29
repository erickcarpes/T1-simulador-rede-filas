#!/usr/bin/env python3
"""Simulador de rede de filas por eventos discretos (T1 | SMA).

Generaliza o simulador de fila única / tandem para qualquer topologia de rede
de filas descrita em um arquivo ``.yml`` no mesmo estilo do simulador de
referência do Módulo 3.

Uso:
    python3 simulador.py modelos/t1.yml
    python3 simulador.py modelos/t1.yml > resultados/t1.txt

A lógica de eventos e a ordem dos sorteios reproduzem o simulador de
referência (Gabriel Couto, 2013):
  * eventos ordenados por tempo, com desempate por ordem de criação (sort estável);
  * em uma chegada, sorteia-se primeiro o roteamento e depois o tempo de
    atendimento (M7);
  * a estatística de cada fila acumula o tempo em todos os estados a cada
    evento (M5/M6);
  * a simulação encerra quando a fonte de números aleatórios se esgota.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


# ---------------------------------------------------------------------------
# Números pseudoaleatórios
# ---------------------------------------------------------------------------


class OutOfNumbers(Exception):
    """Lançada quando um número aleatório é solicitado além do limite."""


class GeradorCongruenteLinear:
    """Gerador pelo Método Congruente Linear (M2): x = (a*x + c) mod M.

    A semente é o valor inicial de ``x`` e cada número devolvido é ``x / M``,
    já normalizado em ``[0, 1)``. O parâmetro ``limite`` define quantos
    números podem ser gerados (critério de parada do T1: 100.000).
    """

    def __init__(
        self,
        semente: int,
        limite: int = 100000,
        a: int = 25214903917,
        c: int = 11,
        m: int = 2 ** 48,
    ) -> None:
        self.a = int(a)
        self.c = int(c)
        self.m = int(m)
        self.x = int(semente)
        self.limite = int(limite)
        self.count = 0

    def has_next(self) -> bool:
        return self.count < self.limite

    def next(self) -> float:
        if not self.has_next():
            raise OutOfNumbers("Acabaram os números aleatórios!")
        self.x = (self.a * self.x + self.c) % self.m
        self.count += 1
        return self.x / self.m

    def __iter__(self) -> "GeradorCongruenteLinear":
        return self

    def __next__(self) -> float:
        return self.next()


class AmostradorEmLista:
    """Fonte determinística de números aleatórios a partir de uma lista."""

    def __init__(self, lista: List[float]) -> None:
        self.lista = [float(v) for v in lista]
        self.i = 0

    def has_next(self) -> bool:
        return self.i < len(self.lista)

    def next(self) -> float:
        if not self.has_next():
            raise OutOfNumbers("Acabaram os números da lista!")
        valor = self.lista[self.i]
        self.i += 1
        return valor

    def __iter__(self) -> "AmostradorEmLista":
        return self

    def __next__(self) -> float:
        return self.next()


# ---------------------------------------------------------------------------
# Eventos e escalonador
# ---------------------------------------------------------------------------


@dataclass
class Evento:
    """Evento temporal: CHEGADA externa ou SAÍDA (para outra fila/exterior)."""

    tempo: float
    tipo: str
    fila: "Fila"
    destino: Optional["Fila"] = None
    id: int = 0


class Fila:
    """Fila com ``servidores`` atendentes, capacidade e roteamento variável."""

    def __init__(self, id: str) -> None:
        self.id = id
        self.ambiente: Optional["Escalonador"] = None
        self.populacao = 0
        self.populacao_max = -1  # -1 => capacidade infinita
        self.servidores = -1
        self.chegada_min = -1.0
        self.chegada_max = -1.0
        self.saida_min = -1.0
        self.saida_max = -1.0
        self.destinos: List[Tuple[float, "Fila"]] = []
        self.estatistica: Dict[int, float] = {}
        self.perdidos = 0
        self.perdidos_entrada = 0
        self.perdidos_passagem = 0
        self.chegadas_aceitas = 0
        self.chegadas_externas = 0
        self.atendidos = 0
        self.saidas_exterior = 0

    # -- roteamento ---------------------------------------------------------

    def add_destino(self, destino: "Fila", probabilidade: float) -> None:
        """Registra uma saída com probabilidade e mantém a ordem crescente."""
        self.destinos.append((float(probabilidade), destino))
        self.destinos.sort(key=lambda par: par[0])

    def get_destino(self) -> Optional["Fila"]:
        """Sorteia o destino de um cliente atendido (roteamento variável).

        Consome um número aleatório, exceto quando há um único destino com
        probabilidade 1,0 (caso em que o destino é determinístico). Devolve
        ``None`` quando o cliente sai da rede (probabilidade restante).
        """
        if not self.destinos:
            return None
        if len(self.destinos) == 1 and self.destinos[0][0] >= 1.0:
            return self.destinos[0][1]
        r = self.ambiente.aleatorio.next()
        for probabilidade, destino in self.destinos:
            if r <= probabilidade:
                return destino
            r -= probabilidade
        return None

    # -- eventos ------------------------------------------------------------

    def chegada(self, agenda_chegada: bool) -> None:
        """Trata a chegada de um cliente (externa ou por passagem)."""
        self.ambiente.contabiliza_tempo()
        if self.populacao_max < 0 or self.populacao < self.populacao_max:
            self.populacao += 1
            self.chegadas_aceitas += 1
            if agenda_chegada:
                self.chegadas_externas += 1
            if self.populacao <= self.servidores:
                # Cliente inicia atendimento: roteamento antes do tempo de serviço.
                self.ambiente.agenda_saida(self, self.get_destino())
        else:
            self.perdidos += 1
            if agenda_chegada:
                self.perdidos_entrada += 1
            else:
                self.perdidos_passagem += 1
        if agenda_chegada:
            self.ambiente.agenda_chegada(self)

    def saida(self) -> None:
        """Trata a conclusão de um atendimento, liberando o servidor."""
        self.ambiente.contabiliza_tempo()
        self.populacao -= 1
        self.atendidos += 1
        if self.populacao >= self.servidores:
            self.ambiente.agenda_saida(self, self.get_destino())

    def __str__(self) -> str:
        return self.id


class Escalonador:
    """Ambiente de simulação: relógio, filas, eventos e estatísticas."""

    def __init__(self) -> None:
        self.eventos: List[Evento] = []
        self.eventos_iniciais: List[Evento] = []
        self.aleatorio = None
        self.tempo = 0.0
        self.last_evt = 0.0
        self.tempo_acumulado = 0.0
        self.em_sistema_acumulado = 0.0
        self.filas: Dict[str, Fila] = {}
        self._evento_id = 0

    # -- construção ---------------------------------------------------------

    def add_fila(self, id: str) -> Fila:
        fila = Fila(id)
        fila.ambiente = self
        self.filas[id] = fila
        return fila

    def get_fila(self, id: str) -> Fila:
        return self.filas[id]

    def _novo_evento(
        self, tempo: float, tipo: str, fila: Fila, destino: Optional[Fila] = None
    ) -> Evento:
        self._evento_id += 1
        return Evento(tempo, tipo, fila, destino, self._evento_id)

    # -- agendamento --------------------------------------------------------

    def agenda_chegada_inicial(self, fila: Fila, instante: float) -> Evento:
        evento = self._agenda_chegada(fila, instante)
        self.eventos_iniciais.append(evento)
        return evento

    def _agenda_chegada(self, fila: Fila, delta: float) -> Evento:
        evento = self._novo_evento(self.tempo + delta, "chegada", fila, None)
        self.eventos.append(evento)
        self.eventos.sort(key=lambda e: e.tempo)
        return evento

    def agenda_chegada(self, fila: Fila) -> Evento:
        u = self.aleatorio.next()
        delta = fila.chegada_min + (fila.chegada_max - fila.chegada_min) * u
        return self._agenda_chegada(fila, delta)

    def _agenda_saida(self, fila: Fila, delta: float, destino: Optional[Fila]) -> Evento:
        evento = self._novo_evento(self.tempo + delta, "saida", fila, destino)
        self.eventos.append(evento)
        self.eventos.sort(key=lambda e: e.tempo)
        return evento

    def agenda_saida(self, fila: Fila, destino: Optional[Fila]) -> Evento:
        u = self.aleatorio.next()
        delta = fila.saida_min + (fila.saida_max - fila.saida_min) * u
        return self._agenda_saida(fila, delta, destino)

    # -- execução -----------------------------------------------------------

    def contabiliza_tempo(self) -> None:
        """Acumula, em todas as filas, o tempo decorrido no estado atual."""
        delta = self.tempo - self.last_evt
        for fila in self.filas.values():
            fila.estatistica[fila.populacao] = (
                fila.estatistica.get(fila.populacao, 0.0) + delta
            )
        self.last_evt = self.tempo

    def step(self) -> None:
        evento = self.eventos.pop(0)
        self.last_evt = self.tempo
        self.tempo = evento.tempo
        if evento.tipo == "chegada":
            evento.fila.chegada(True)
        else:
            evento.fila.saida()
            if evento.destino is not None:
                evento.destino.chegada(False)
            else:
                evento.fila.saidas_exterior += 1

    def reset(self) -> None:
        """Prepara uma nova réplica, acumulando o tempo e as estatísticas."""
        self.eventos = []
        self.tempo_acumulado += self.tempo
        self.em_sistema_acumulado += sum(
            fila.populacao for fila in self.filas.values()
        )
        self.tempo = 0.0
        self.last_evt = 0.0
        for fila in self.filas.values():
            fila.populacao = 0
        self.eventos.extend(self.eventos_iniciais)

    def tempo_global(self) -> float:
        return self.tempo + self.tempo_acumulado

    def verifica_conservacao(self) -> Tuple[float, float]:
        """Confere a conservação de clientes na rede.

        Devolve ``(aceitos_externos, saidas + perdas_passagem + em_sistema)``.
        """
        aceitos = sum(fila.chegadas_externas for fila in self.filas.values())
        saidas = sum(fila.saidas_exterior for fila in self.filas.values())
        perdas_passagem = sum(
            fila.perdidos_passagem for fila in self.filas.values()
        )
        return aceitos, saidas + perdas_passagem + self.em_sistema_acumulado


# ---------------------------------------------------------------------------
# Leitura do modelo (.yml)
# ---------------------------------------------------------------------------


class SFila:
    """Configuração de uma fila lida do arquivo."""

    def __init__(self) -> None:
        self.capacity = -1
        self.servers = -1
        self.min_arrival = -1.0
        self.max_arrival = -1.0
        self.min_service = -1.0
        self.max_service = -1.0


class SDestino:
    """Uma aresta de roteamento ``source -> target`` com probabilidade."""

    def __init__(self, source: str, target: str, probability: float) -> None:
        self.source = source
        self.target = target
        self.probability = float(probability)


class ParametrosSimulador:
    """Modelo completo lido do ``.yml``."""

    def __init__(self) -> None:
        self.queues: Dict[str, SFila] = {}
        self.network: List[SDestino] = []
        self.arrivals: Dict[str, float] = {}
        self.rndnumbers: List[float] = []
        self.seeds: List[int] = []
        self.rndnumbers_per_seed = 100000
        self.a = 25214903917
        self.c = 11
        self.m = 2 ** 48


# Alvos que representam a saída da rede. A probabilidade restante de cada
# fila já é, por convenção, encaminhada ao exterior (como no simulador de
# referência), logo esses alvos são ignorados no roteamento.
ALVOS_EXTERIOR = {"exterior", "external", "out", "saida", "saída", "fora"}


def _carregador_yaml():
    class Loader(yaml.SafeLoader):
        pass

    Loader.add_constructor(
        "!PARAMETERS", lambda loader, node: loader.construct_mapping(node, deep=True)
    )
    return Loader


def carrega_parametros(caminho: str) -> ParametrosSimulador:
    if yaml is None:
        raise RuntimeError("PyYAML é necessário para ler o arquivo .yml")
    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = yaml.load(arquivo, Loader=_carregador_yaml()) or {}

    parametros = ParametrosSimulador()

    for qid, config in (dados.get("queues") or {}).items():
        config = config or {}
        fila = SFila()
        fila.capacity = int(config.get("capacity", -1))
        fila.servers = int(config.get("servers", -1))
        fila.min_arrival = float(config.get("minArrival", -1.0))
        fila.max_arrival = float(config.get("maxArrival", -1.0))
        fila.min_service = float(config.get("minService", -1.0))
        fila.max_service = float(config.get("maxService", -1.0))
        parametros.queues[qid] = fila

    for aresta in dados.get("network") or []:
        parametros.network.append(
            SDestino(aresta["source"], aresta["target"], aresta["probability"])
        )

    for qid, instante in (dados.get("arrivals") or {}).items():
        parametros.arrivals[qid] = float(instante)

    for valor in dados.get("rndnumbers") or []:
        parametros.rndnumbers.append(float(valor))

    for semente in dados.get("seeds") or []:
        parametros.seeds.append(int(semente))

    if dados.get("rndnumbersPerSeed") is not None:
        parametros.rndnumbers_per_seed = int(dados["rndnumbersPerSeed"])

    parametros.a = int(dados.get("a", dados.get("multiplier", parametros.a)))
    parametros.c = int(dados.get("c", dados.get("increment", parametros.c)))
    parametros.m = int(dados.get("m", dados.get("modulus", parametros.m)))

    return parametros


def converte_ambiente(parametros: ParametrosSimulador) -> Escalonador:
    """Monta o ambiente de simulação a partir dos parâmetros do modelo."""
    ambiente = Escalonador()

    for qid, config in parametros.queues.items():
        fila = ambiente.add_fila(qid)
        fila.populacao_max = config.capacity
        fila.servidores = config.servers
        fila.chegada_min = config.min_arrival
        fila.chegada_max = config.max_arrival
        fila.saida_min = config.min_service
        fila.saida_max = config.max_service

    for aresta in parametros.network:
        if aresta.target.strip().lower() in ALVOS_EXTERIOR:
            continue
        origem = ambiente.get_fila(aresta.source)
        destino = ambiente.get_fila(aresta.target)
        origem.add_destino(destino, aresta.probability)

    for qid, instante in parametros.arrivals.items():
        ambiente.agenda_chegada_inicial(ambiente.get_fila(qid), instante)

    ambiente.aleatorio = AmostradorEmLista(parametros.rndnumbers)
    return ambiente


def valida_roteamento(parametros: ParametrosSimulador) -> List[str]:
    """Verifica que a soma das probabilidades por fila não excede 1."""
    avisos = []
    somas: Dict[str, float] = {}
    for aresta in parametros.network:
        if aresta.target.strip().lower() in ALVOS_EXTERIOR:
            continue
        somas[aresta.source] = somas.get(aresta.source, 0.0) + aresta.probability
    for origem in parametros.queues:
        soma = somas.get(origem, 0.0)
        if soma > 1.0 + 1e-9:
            avisos.append(
                f"ATENÇÃO: soma das probabilidades da fila {origem} = {soma:.4f} > 1"
            )
    return avisos


# ---------------------------------------------------------------------------
# Simulação e relatório
# ---------------------------------------------------------------------------


def simula(parametros: ParametrosSimulador) -> Tuple[Escalonador, int]:
    """Executa uma réplica por semente (ou uma com ``rndnumbers``)."""
    ambiente = converte_ambiente(parametros)
    simulacoes = len(parametros.seeds) if parametros.seeds else 1

    for indice in range(simulacoes):
        if parametros.seeds:
            ambiente.aleatorio = GeradorCongruenteLinear(
                parametros.seeds[indice],
                parametros.rndnumbers_per_seed,
                parametros.a,
                parametros.c,
                parametros.m,
            )
        else:
            ambiente.aleatorio = AmostradorEmLista(parametros.rndnumbers)

        try:
            while ambiente.aleatorio.has_next():
                ambiente.step()
        except OutOfNumbers:
            pass
        ambiente.reset()

    return ambiente, simulacoes


def _formata_titulo_fila(fila: Fila) -> str:
    if fila.populacao_max < 0:
        return f"{fila} (G/G/{fila.servidores})"
    return f"{fila} (G/G/{fila.servidores}/{fila.populacao_max})"


def imprime_relatorio(ambiente: Escalonador, simulacoes: int, fluxo) -> None:
    tempo_total = ambiente.tempo_global()

    print("=" * 57, file=fluxo)
    print("          RELATORIO DA SIMULACAO - REDE DE FILAS", file=fluxo)
    print("=" * 57, file=fluxo)

    for fila in ambiente.filas.values():
        print("*" * 57, file=fluxo)
        print(f"Fila: {_formata_titulo_fila(fila)}", file=fluxo)
        if fila.chegada_min >= 0.0:
            print(
                f"Chegadas: {fila.chegada_min:.1f} ... {fila.chegada_max:.1f}",
                file=fluxo,
            )
        print(
            f"Atendimento: {fila.saida_min:.1f} ... {fila.saida_max:.1f}", file=fluxo
        )
        if fila.destinos:
            rotas = "  ".join(
                f"{probabilidade:.2f}->{destino}"
                for probabilidade, destino in fila.destinos
            )
            print(f"Roteamento: {rotas}  (restante -> exterior)", file=fluxo)
        else:
            print("Roteamento: 1.00->exterior", file=fluxo)
        print("-" * 57, file=fluxo)
        print(f"{'Estado':>7}{'Tempo':>20}{'Probabilidade':>18}", file=fluxo)
        for estado in sorted(fila.estatistica):
            tempo_estado = fila.estatistica[estado]
            probabilidade = 100.0 * tempo_estado / tempo_total if tempo_total else 0.0
            print(
                f"{estado:>7}{tempo_estado:>20.4f}{probabilidade:>17.2f}%",
                file=fluxo,
            )
        populacao_media = 0.0
        for estado, tempo_estado in fila.estatistica.items():
            populacao_media += estado * tempo_estado
        populacao_media = populacao_media / tempo_total if tempo_total else 0.0
        print(f"\nNumero de perdas: {fila.perdidos}", file=fluxo)
        print(f"Populacao media: {populacao_media:.4f}", file=fluxo)
        print(file=fluxo)

    print("=" * 57, file=fluxo)
    print(f"Tempo global da simulacao: {tempo_total:.4f}", file=fluxo)
    if simulacoes > 1:
        print(
            f"Tempo medio por simulacao: {tempo_total / simulacoes:.4f}", file=fluxo
        )
    print("=" * 57, file=fluxo)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Simulador de rede de filas (eventos discretos)."
    )
    parser.add_argument("modelo", help="arquivo .yml com o modelo da rede")
    parser.add_argument(
        "-o", "--saida", help="arquivo de saida (padrao: stdout)", default=None
    )
    args = parser.parse_args(argv)

    parametros = carrega_parametros(args.modelo)
    for aviso in valida_roteamento(parametros):
        print(aviso, file=sys.stderr)

    ambiente, simulacoes = simula(parametros)

    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as fluxo:
            imprime_relatorio(ambiente, simulacoes, fluxo)
    else:
        imprime_relatorio(ambiente, simulacoes, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
