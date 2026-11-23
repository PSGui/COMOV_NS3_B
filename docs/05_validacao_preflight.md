# Validação independente dos ficheiros do preflight — 2026-11-23

**Âmbito:** ficheiros CSV enviados pelo grupo após execução local do `scripts/preflight.py`. Isto valida cálculos analíticos e estrutura de experiências; **não é validação da simulação ns-3**. A saída do terminal não foi fornecida.

## Resultados

| Ficheiro | Linhas de dados | Teste realizado | Resultado |
|---|---:|---|---|
| `matrix.csv` | 12 | Produto cartesiano de 2 velocidades × 3 paragens × 2 políticas; IDs B10-01…12; timestamps e 10 repetições uniformes | OK |
| `theory.csv` | 14 | Recalcular FSPL, log-distance com n=3, d0=1 m e `Pr=20-PL` para 7 distâncias × 2 frequências | OK; desvio inferior ao arredondamento (1e-5 dB) |
| `contact_examples.csv` | 12 | Recalcular `2R/v+s` para R=50/100 m e v=5/15 m/s, s=0/10/30 s | OK; desvio inferior a 6e-6 s |

Consistência: `theory.csv` apresenta, para 50 m, `Pr≈-71,06443 dBm` a 2,412 GHz e `Pr≈-77,70348 dBm` a 5,180 GHz, diferença de **6,63905 dB**. Isto é **potência prevista**, não nível de cobertura confirmado, probabilidade de receção ou resultado de ns-3.

## Observação técnica para o piloto

Com a configuração provisória, a geração começa em `t=10 s` e a paragem em `t=70 s`. O buffer de 4 MB corresponde a 40 segundos de mensagens (100 × 1000 bytes/s).

No caso *ilustrativo* de cobertura horizontal R=50 m e AP em x=0:

| v (m/s) | t de entrada geométrica (s) | Mensagens geradas antes da entrada | Dados gerados | Excesso teórico sobre buffer |
|---:|---:|---:|---:|---:|
| 5 | 60,0 | 5000 | 5,00 MB | 1,00 MB |
| 15 | 66,67 | ≈5667 | ≈5,67 MB | ≈1,67 MB |

A associação real só ocorrerá **depois ou durante** a oportunidade geométrica e pode introduzir atraso adicional. Portanto, **poderá haver overflow antes do primeiro contacto útil**, mesmo sem retransmissões nem tráfego concorrente. Isto não invalida o estudo, mas impede interpretar descarte pré-associação como perda por propagação.

Para um raio hipotético de 100 m: a 5 m/s o contacto começa em t=50 s (4 MB já produzidos); qualquer atraso de associação ou insuficiência de escoamento poderá causar overflow. A 15 m/s começa em t≈63,33 s (≈5,33 MB já gerados).

**Condição geométrica de não-excedência do buffer antes do contacto:** `R >= v*(t_stop-t_gen_start-B/R_gen) = 20v` para estes parâmetros, ou R≥100 m (5 m/s) e R≥300 m (15 m/s). Mesmo satisfazendo a condição, é possível overflow devido ao tempo de associação e ao ritmo de envio inferior à geração.

## Precisão e interpretação geométrica

- `distance_m` em `theory.csv` é a **distância tridimensional efetiva entre antenas**, não necessariamente a distância longitudinal do autocarro ao AP.
- Com alturas de 4 m (AP) e 2,5 m (autocarro), a distância mínima entre antenas ao passar junto do AP é 1,5 m, não 0 nem 1 m. Não comparar `Pr(1 m)` desse CSV com uma trace do autocarro parado em x=0.
- Os raios 50/100 m de `contact_examples.csv` são **hipóteses geométricas**, não margens/SNR estimados nem cobertura operacional real.
- Para comparar com ns-3, usar `d=sqrt((x_bus-x_AP)^2+(z_bus-z_AP)^2)` e incluir as opções efetivas de canal, perdas e modelo PHY.
- IC95%, perdas, PDR, associação, tempo útil e goodput **não podem ser validados pelos CSV atuais**, porque exigem execução ns-3 e eventos reais do simulador.

## Proveniência dos CSV revistos

SHA-256 (ficheiros fornecidos ao longo da conversa, não versionados no Git):

```text
matrix.csv            ac45a617597651bda01f84bc5306f1e3ce8b39c2689196d7ce848bea5f597688
theory.csv            cdd7f86cac3ce3e80a307921aa3fb7d131b8eecfb400ba0e5bcdbe249f3562d2
contact_examples.csv  3d7102b76f9923821017e929a2888c064b8786bafcbdc98be96cae0d39c61a5a
```

## Próxima validação: P0

Instalar/confirmar versão do ns-3 no WSL, fixar os modos PHY e a referência `ReferenceLoss` à frequência usada, medir RSS em distâncias conhecidas e comparar com os valores calculados **à distância tridimensional correta**. Só depois avançar para mobilidade e associação.
