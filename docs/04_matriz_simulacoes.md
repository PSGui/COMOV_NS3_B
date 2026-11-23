# Matriz obrigatória, piloto, robustez e protocolo de análise

## 1. Matriz B10 (obrigatória)

| ID | v (m/s) | Paragem (s) | Envio imediato | Buffer FIFO | Repetições iniciais |
|---|---:|---:|---|---|---:|
| B10-01/02 | 5 | 0 | B10-01 | B10-02 | 10 por política |
| B10-03/04 | 5 | 10 | B10-03 | B10-04 | 10 por política |
| B10-05/06 | 5 | 30 | B10-05 | B10-06 | 10 por política |
| B10-07/08 | 15 | 0 | B10-07 | B10-08 | 10 por política |
| B10-09/10 | 15 | 10 | B10-09 | B10-10 | 10 por política |
| B10-11/12 | 15 | 30 | B10-11 | B10-12 | 10 por política |

Total inicial: **12 configurações × 10 = 120 execuções**; 60 pares. Os pares partilham geração, mobilidade e entradas externas; **as execuções entre pares são independentes**. O piloto deve indicar se é preciso mais do que dez runs para a precisão desejada.

## 2. Piloto, por ordem

| Piloto | Objetivo | Critério para avançar |
|---|---|---|
| P0 — física, AP e STA fixos | `Pr(d)` vs teórico em distâncias escolhidas; taxa PHY efetiva | discrepância explicada e parâmetro identificado |
| P1 — autocarro em movimento, imediato | trajetória, associação/desassociação, gerações e receções, sem retenção na app | logs coerentes e IDs contabilizados |
| P2 — FIFO | overflow, FIFO, associação, pacing e diferença entre entrega tardia e oportuna | assert de conservação de mensagens |
| P3 — casos crítico/leve | saturação, ocupação, tempo de simulação e precisão | fixar pacing, duração e streams antes do lote principal |
| P4 — reprodutibilidade | repetir exatamente um run com mesmo seed/run/stream | arquivos coincidem ou diferenças controladas justificadas |

## 3. Sequência do lote principal

1. Fixar `ns-3 version`, dependências, parâmetros, `seed`, `run`, streams e pontos de mobilidade.
2. Para cada `run_id=1..n`, executar 12 combinações com `run_id` associado e entradas externas idênticas nas políticas emparelhadas.
3. Conservar CSV/JSON brutos da aplicação, eventos de associação e traços PHY/MAC necessários; **não apagar runs com zero entrega**.
4. Manter runs falhados/sem associação com classificação explícita; run sem evento esperado pode ser válido, run com erro não é válido.
5. Calcular por run volume único, entrega <=60s, tempo útil, goodput, ocupação máxima, descartes e mensagens pendentes.
6. Computar diferenças por par e IC95%, mediana e percentis de atraso apenas das mensagens efetivamente recebidas (interpretando-os ao lado da taxa de perda).

## 4. Robustez obrigatória

Deslocar AP ao longo da estrada (deslocamentos propostos `-30m` e `+30m`; escolher duas condições críticas após piloto). Manter todo o resto equivalente. A deslocação pode mudar assimetricamente contacto antes/depois da paragem — **é esse efeito que se pretende estudar**. Comparar ao cenário central sem reajustar o buffer.

## 5. Extensão opcional 802.11a vs 802.11g

**Só depois do estudo principal:** repetir, no mínimo, um caso de contacto curto e outro com fila relevante em ambos os padrões e políticas, com taxa PHY nominal comum de 6 Mbit/s e restantes parâmetros comparáveis. Recalcular FSPL e sensibilidade/ruído à banda real, e discriminar o que mudou. Não reduzir a matriz obrigatória por causa desta extensão.

## 6. Figuras prioritárias (evitar gráficos sem interpretação)

1. **Mapa/linha da trajetória:** AP, autocarro, cobertura apenas **estimada**, tempos de associação reais, início/fim da paragem;
2. **Gráfico em painéis alinhados por associação:** buffer (kB), receções por segundo e estado da associação (mostrar política e condições);
3. **6 pares:** volume único/passagem (MB) + diferenças e IC95%, velocidades e tempos de paragem;
4. **Entrega em 60 s:** percentagem = receções até 60 s / geradas; linha da meta **apenas se houver requisito explícito**;
5. **Modelo independente vs resultado:** estimativa de bytes vs entregues, reta 1:1 e erro numérico;
6. **Balanço de mensagens:** entregues no prazo / entregues tarde / descartadas / pendentes (somam geradas);
7. **Robustez:** ganho do buffer com AP central vs deslocado;
8. **Opcional:** a/g, distinguindo efeito frequência, perfil de perdas e PHY.

## 7. Campos brutos propostos

`messages.csv`: `run_id,config_id,policy,message_id,t_gen_s,t_app_send_s,t_first_rx_s,app_drop_reason,final_state,deadline_met`.
`association.csv`: `run_id,config_id,t_s,station_id,ap_id,event`.
`buffer.csv`: `run_id,config_id,t_s,occupancy_bytes,queued_messages,event,message_id`.
`mobility.csv`: `run_id,config_id,t_s,x_m,y_m,z_m,v_mps,d_ap_m`.
`phy.csv` / `mac.csv`: campos definidos pelos trace sources reais da versão ns-3, sem inventar eventos.
`runs.csv`: `config_id,run_id,seed,streams,ns3_version,exit_status,validity,reason,input_hash,output_paths`.

**Importante:** o CSV final por mensagem exige instrumentação de eventos; não se obtém uma classificação fiável de todas as mensagens apenas com FlowMonitor. Guardar logs originais e scripts de agregação.
