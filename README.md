# T1 — Simulador para Rede de Filas

Simulador de eventos discretos em **Python 3**, generalizado para **qualquer
topologia de rede de filas**, com entrada em `.yml` no estilo do simulador de
referência do Módulo 3. Produz o relatório pedido pelo T1: tempo acumulado e
probabilidade de cada estado por fila, número de perdas por fila e tempo global
da simulação.

## Modelo do T1

- **Fila 1** — `G/G/1` (capacidade infinita), chegadas `2..4`, atendimento `1..2`;
  roteamento `0,2 → F2` e `0,8 → F3`.
- **Fila 2** — `G/G/2/5`, atendimento `4..6`; roteamento `0,3 → F1`, `0,5 → F3`,
  `0,2 → exterior`.
- **Fila 3** — `G/G/2/10`, atendimento `5..15`; roteamento `0,7 → F2`,
  `0,3 → exterior`.

Filas inicialmente vazias, 1ª chegada em `t = 2,0` e parada ao consumir
`100.000` números aleatórios (semente `42`).

## Como executar

```bash
pip install pyyaml
python3 simulador.py modelos/t1.yml          # imprime o relatório
python3 simulador.py modelos/t1.yml -o resultados/t1.txt
python3 testes.py                            # 10 testes (inclui o vetor do E1)
```

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `simulador.py` | Simulador (LCG, escalonador, fila, leitura `.yml`, relatório). |
| `testes.py` | Testes `unittest`, com valores conferidos contra o `simulator.jar`. |
| `INSTRUCOES.md` | Instruções de uso e formato do `.yml`. |
| `modelos/t1.yml` | Modelo do T1. |
| `modelos/exemplo.yml`, `modelos/exemplo_rnd.yml` | Modelo de 4 filas (validação). |
| `modelos/e1.yml` | Vetor determinístico do E1. |
| `resultados/t1.txt` | Relatório completo do T1. |
| `resultados/t1_resumo.txt` | Resumo no formato do arquivo-modelo do T1. |
| `resultados/t1_referencia.txt`, `resultados/exemplo_referencia.txt` | Saídas do simulador de referência usadas como golden. |

## Validação

Os resultados coincidem exatamente com o simulador de referência
(`simulator.jar`) nos três modelos conferidos — vetor do E1, exemplo de 4 filas
(com lista explícita e com 5 sementes) e o modelo do T1. Detalhes em
[`INSTRUCOES.md`](INSTRUCOES.md).
