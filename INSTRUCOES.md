# Instruções de uso — Simulador de Rede de Filas (T1)

Simulador de eventos discretos em **Python 3** para **qualquer topologia de
rede de filas**. O modelo é descrito em um arquivo `.yml` no mesmo estilo do
simulador de referência do Módulo 3.

## 1. Requisitos

- Python 3.8 ou superior.
- Biblioteca **PyYAML** (para ler o `.yml`):

  ```bash
  pip install pyyaml
  ```

Nenhuma outra dependência é necessária.

## 2. Como executar

```bash
# imprime o relatório na tela
python3 simulador.py modelos/t1.yml

# salva o relatório em arquivo
python3 simulador.py modelos/t1.yml > resultados/t1.txt
python3 simulador.py modelos/t1.yml -o resultados/t1.txt
```

Arquivos prontos:

| Arquivo | Descrição |
|---|---|
| `modelos/t1.yml` | Modelo do T1 (F1 G/G/1, F2 G/G/2/5, F3 G/G/2/10), semente 42, 100.000 aleatórios. |
| `modelos/exemplo.yml` | Exemplo de 4 filas do Módulo 3 (5 sementes) — validação. |
| `modelos/exemplo_rnd.yml` | Mesmo exemplo, com lista explícita de aleatórios — validação determinística. |
| `modelos/e1.yml` | Vetor determinístico do E1 (G/G/1/3). |
| `resultados/t1.txt` | Relatório completo do T1 produzido pelo simulador. |
| `resultados/t1_resumo.txt` | Resumo do T1 no formato pedido pelo arquivo-modelo. |
| `resultados/t1_referencia.txt` | Saída do simulador de referência para o `t1.yml` (comparação). |
| `resultados/exemplo_referencia.txt` | Saída de referência para o `exemplo.yml`. |

Para rodar os testes (10 verificações, incluindo comparação com o simulador de
referência):

```bash
python3 testes.py
```

## 3. Formato do arquivo `.yml`

O arquivo deve começar com a linha de marcação `!PARAMETERS` (necessária para o
simulador de referência; é ignorada pelo nosso). Exemplo:

```yaml
!PARAMETERS

arrivals:            # fila -> instante da 1a chegada externa (não consome aleatório)
   F1: 2.0

queues:              # capacidade ausente => infinita
   F1:
      servers: 1
      minArrival: 2.0
      maxArrival: 4.0
      minService: 1.0
      maxService: 2.0
   F2:
      servers: 2
      capacity: 5
      minService: 4.0
      maxService: 6.0
   F3:
      servers: 2
      capacity: 10
      minService: 5.0
      maxService: 15.0

network:             # roteamento; a soma < 1 vira saída da rede (exterior)
-  source: F1
   target: F2
   probability: 0.2
-  source: F1
   target: F3
   probability: 0.8
-  source: F2
   target: F1
   probability: 0.3
-  source: F2
   target: F3
   probability: 0.5
-  source: F3
   target: F2
   probability: 0.7

# Números aleatórios: use 'rndnumbers' OU 'seeds' + 'rndnumbersPerSeed'.
# Se 'seeds' estiver presente, 'rndnumbers' é ignorado (como na referência).
rndnumbersPerSeed: 100000
seeds:
- 42
```

### Campos

- **`arrivals`** — instante absoluto da primeira chegada externa de cada fila.
  Não consome número aleatório. Apenas filas listadas recebem clientes do
  exterior.
- **`queues`** — uma entrada por fila:
  - `servers`: número de atendentes (obrigatório);
  - `capacity`: número máximo de clientes **no sistema** (em atendimento +
    espera). Se ausente, a fila é infinita;
  - `minArrival` / `maxArrival`: intervalo entre chegadas externas (só para
    filas com `arrivals`);
  - `minService` / `maxService`: tempo de atendimento.
- **`network`** — arestas de roteamento `source -> target` com `probability`.
  A soma das probabilidades de cada fila **não precisa ser 1**: a parte que
  faltar é encaminhada ao **exterior** (mesma convenção do simulador de
  referência). Também é aceito um destino explícito `EXTERIOR` (ou
  `EXTERNAL`/`FORA`/`SAIDA`), que é simplesmente ignorado no roteamento, pois o
  restante já vai para fora.
- **`rndnumbers`** — lista explícita de números em `[0,1)` (validação).
- **`seeds`** + **`rndnumbersPerSeed`** — geração automática. Uma simulação é
  executada por semente e as estatísticas são agregadas; `rndnumbersPerSeed`
  define o limite de aleatórios por semente (no T1, uma semente e 100.000).
- **Parâmetros do gerador (opcionais)** — `a`, `c`, `m` (ou `multiplier`,
  `increment`, `modulus`). Padrão: `a = 25214903917`, `c = 11`, `m = 2^48`, o
  mesmo gerador congruente linear do simulador de referência.

## 4. Gerador de números aleatórios

Método Congruente Linear (M2):

```
x_{n+1} = (a * x_n + c) mod M
U_n     = x_n / M
```

A semente é o valor inicial de `x`. O intervalo `U(a,b)` é gerado por
`a + (b - a) * U_n`.

## 5. Lógica da simulação

- **Eventos**: CHEGADA externa e SAÍDA (para outra fila — passagem — ou para o
  exterior). Uma `SAÍDA` guarda o destino sorteado quando o atendimento
  começa.
- **Ordem dos sorteios**: ao iniciar um atendimento, sorteia-se **primeiro o
  roteamento** (destino) e **depois o tempo de atendimento** (M7). Na chegada
  externa, o intervalo até a próxima chegada é sorteado por último.
- **Capacidade**: o estado de uma fila é o número de clientes no sistema
  (`0..capacity`). Uma chegada (externa ou passagem) em fila cheia é
  **perdida**. Fila de capacidade infinita nunca perde.
- **Estatística**: a cada evento, todas as filas acumulam o tempo decorrido no
  estado atual (M5/M6). A probabilidade de um estado é `tempo_no_estado /
  tempo_global`.
- **Parada**: quando a fonte de aleatórios se esgota (no T1, ao usar o
  100.000º número o passo corrente termina e a simulação encerra).

## 6. Saída

Para cada fila o relatório mostra `Fila (G/G/servidores[/capacidade])`,
intervalos de chegada/atendimento, roteamento, uma tabela
**Estado / Tempo acumulado / Probabilidade**, o **número de perdas** e a
**população média**. Ao final: **tempo global da simulação** (e o tempo médio
por simulação quando há mais de uma semente).

## 7. Validação

O simulador foi comparado com o `simulator.jar` de referência:

- `modelos/exemplo_rnd.yml` (lista explícita): resultados **idênticos**;
- `modelos/exemplo.yml` (5 sementes): resultados **idênticos**, incluindo as
  6.244 perdas da fila Q2;
- `modelos/t1.yml` (semente 42, 100.000 aleatórios): resultados **idênticos**
  (tempo global 50684,4435; perdas 0 / 3 / 11614).

Também são verificadas a faixa `[0,1)` e a reprodutibilidade do gerador, a soma
do roteamento por fila, a conservação de clientes e a ausência de perdas na
Fila 1 (capacidade infinita). Rode `python3 testes.py` para reproduzir.
