# Modelo teórico independente — B10

**Estatuto:** previsões analíticas **não** substituem simulação ns-3. Usar valores de `params/reference.json`. Convenção: MB = 10^6 bytes; 4 MB = 4 000 000 bytes.

## 1. Geração e buffer

Se N=100 mensagens/s e L=1000 bytes de payload **total** por mensagem (inclui ID e timestamp):

```text
lambda = 100 mensagens/s
R_app = lambda * L * 8 = 800 000 bit/s = 0,8 Mbit/s = 100 000 byte/s
T_gen = 130-10 = 120 s
N_gen = 12000 mensagens
V_gen = 12 000 000 bytes = 12 MB = 96 Mbit
B = 4 000 000 bytes = 4000 mensagens = 40 s sem escoamento
```

**Não confundir:** 1000 bytes de payload com 1000 bytes de frame MAC, UDP ou IP. Overheads de cabeçalhos, preâmbulos, ACK e retransmissões impedem obter 6 Mbit/s de goodput a partir de 6 Mbit/s PHY.

## 2. Percurso e distância ao AP

A paragem começa em t_s=70 s e dura s segundos; para velocidade v (m/s), posição longitudinal:

```text
x(t)=v*(t-t_s)                    t<t_s
x(t)=0                            t_s<=t<t_s+s
x(t)=v*(t-t_s-s)                  t>=t_s+s
d(t)=sqrt((x(t)-x_AP)^2 + (4.0-2.5)^2)
```

No caso AP em x_AP=0 e cobertura horizontal ideal de raio R (não é constante de ns-3):

```text
T_geo = 2R/v + s
t_entrada = t_s - R/v
t_saida = t_s+s+R/v
```

Para AP deslocado (`x_AP != 0`) a geometria de contacto **deve ser recalculada** e a fórmula simples é apenas referência quando se atravessa o intervalo completo, sem cortes pela janela de observação. Não confundir `T_geo`, `T_assoc` e `T_util`.

| R hipotético | v | s=0 | s=10 | s=30 |
|---:|---:|---:|---:|---:|
| 50 m | 5 m/s | 20,00 s | 30,00 s | 50,00 s |
| 50 m | 15 m/s | 6,67 s | 16,67 s | 36,67 s |
| 100 m | 5 m/s | 40,00 s | 50,00 s | 70,00 s |
| 100 m | 15 m/s | 13,33 s | 23,33 s | 43,33 s |

Os raios 50/100 m são **hipóteses ilustrativas**, não resultados de cobertura.

## 3. Frequência, FSPL, log-distance e potência recebida

Para referência d0=1 m, frequência f e velocidade da luz c:

```text
lambda_RF = c/f
FSPL(d0)[dB] = 20*log10(4*pi*f*d0/c)
PL(d)[dB] = FSPL(d0)+10*n*log10(d/d0), d>=d0
Pr(d)[dBm] = Ptx + Gtx+Grx-Ltx-Lrx-PL(d)
M(d)[dB] = Pr(d)-S_rx
PLmax = Ptx + Gtx+Grx-Ltx-Lrx-S_rx-F_margin
d_max = d0 * 10^((PLmax-FSPL(d0))/(10*n))
```

Para d<d0, não extrapolar cegamente o log-distance; confirmar o tratamento do modelo da versão ns-3. Exemplos **sem limiar de descodificação** com Ptx=20 dBm, ganhos/perdas=0 e n=3:

| Freq. | FSPL(1m) aprox. | PL(50m) aprox. | Pr(50m) aprox. |
|---|---:|---:|---:|
| 2,412 GHz | 40,09 dB | 91,06 dB | -71,06 dBm |
| 5,180 GHz | 46,74 dB | 97,71 dB | -77,71 dBm |

Diferença de perdas FSPL = 20log10(5,180/2,412) ≈ 6,64 dB. **802.11a vs g:** altera simultaneamente frequência, parâmetros da norma e eventualmente limiares físicos; não atribuir diferenças exclusivamente ao "protocolo".

A potência recebida não determina, sozinha, se um pacote UDP chega: taxa/modulação, SNR, ruído, modelo de erro PHY, beacons, associação, MAC e filas importam. Estimar alcance via sensibilidade/margem somente **depois** de escolher e justificar os valores.

## 4. Ruído e perdas/qualidade

```text
N_dBm ≈ -174 + 10log10(B_Hz) + NF_dB   (T≈290 K)
SNR_dB = Pr_dBm - N_dBm
SINR_linear = Ps/(N+I)
Doppler_max ≈ v*f/c
```

Exemplo aritmético sem inferência de desempenho: com B=20 MHz, `N_thermal ≈ -100,99 dBm` antes do noise figure. Para NF=7 dB (apenas ilustração), `N≈-93,99 dBm`. Doppler máximo teórico a 15 m/s: ≈120,7 Hz em 2,412 GHz; ≈259,2 Hz em 5,180 GHz. **Não afirmar que o modelo escolhido reproduz fading/Doppler só por calcular estes indicadores.**

## 5. Tempo útil, capacidade e limites

```text
T_util = medida dos intervalos associados com possibilidade de transmissão
T_util <= T_geo             (sob a hipótese simplificada de cobertura escolhida)
V_cap_ideal [bytes] <= G_contact [bit/s]*T_util/8
G_contact [bit/s] = 8*unique_payload_bytes_received_during_contact / T_util
```

**Circularidade a evitar:** não validar o próprio goodput medido usando o mesmo goodput medido como previsão. Para previsão independente usar `G_contact` de um teste de referência estacionário pré-definido ou um modelo de airtime que inclua cabeçalhos, ACK, interframe spaces, contention e PHY.

Num intervalo `[t1,t2]` com taxa de serviço ideal `mu(t)` em mensagens/s e gerações `lambda(t)`, o backlog aproxima-se por:

```text
dQ/dt = lambda(t) - mu(t)     enquanto 0<Q<B/L
Q(t) >= 0; Q(t) <= B/L
drop_newest quando Q = B/L e chega outra mensagem
```

Este modelo fluido é aproximado: associação, filas inferiores, eventos discretos, atrasos e retransmissões não são capturados. A janela de 60 s pode ser violada mesmo quando há entrega eventual.

## 6. Métricas e reconciliação

ID único = (`bus_id`, `message_seq`), sem reutilização entre runs. Data de geração **antes de enfileirar**.

```text
on_time_i = 1 se a primeira receção única tem t_rx - t_gen <= 60 s; caso contrário 0
P_on_time = sum(on_time_i) / N_gen
V_unique_pass = 1000 * N_unique_delivered_in_pass
D_i = t_first_rx - t_gen
G_contact = 8*V_unique_received_during_contact/T_util
```

Uma mensagem pode ser entregue **tarde** e continuar a contar no volume único; separar `delivered_on_time` de `delivered_late`. Para o prazo de 60 s, simular até `t_end_generation +60s` **pelo menos**, e idealmente mais para observar pendentes. Considerar receções até `t_obs_end` na classe `delivered_late`.

**Estados mutuamente exclusivos ao fim da observação:**

```text
N_generated = N_delivered_unique + N_dropped_before_delivery + N_pending_undelivered
N_delivered_unique = N_delivered_on_time + N_delivered_late
```

Se o pacote teve rejeição no `socket.Send`, registar a tentativa e definir a sua disposição final. Não somar novamente pacotes MAC falhados que pertençam a uma mensagem já entregue. Estado `pending` requer desagregação: em buffer / enviada sem confirmação / na fila inferior / desconhecido. Quando o MAC descarta, registar como motivo causal, **mas não assumir que todo drop PHY se converte imediatamente num drop final da mensagem**.

## 7. Estatística de diferenças emparelhadas

Cada run é **uma** observação. Para `n>=10` pares independentes:

```text
Delta_i = metric_buffer_i - metric_immediate_i
MeanDelta = sum(Delta_i)/n
sDelta = sqrt(sum((Delta_i-MeanDelta)^2)/(n-1))
IC95% = MeanDelta +/- t_(0.975,n-1) * sDelta/sqrt(n)
```

Reportar ganhos de PDR em **pontos percentuais** (não "percentagem de melhoria") e volume em MB. Não calcular IC tratando milhares de pacotes da mesma execução como amostras independentes.

## 8. Critérios de validação independente

1. Comparar `Pr(d)` calculado à parte com RSS/PHY trace em pelo menos 3 distâncias, contabilizando referência, alturas, antenas e quaisquer perdas extra.
2. Confirmar sequência e temporização de mobilidade e eventos de associação/desassociação.
3. Comparar 100 msg/s com IDs no CSV de geração e 12 000 totais na janela.
4. Reconciliar os estados por ID; documentar e corrigir qualquer discrepância.
5. Para cada run, confrontar volumes estimados **sem realimentar goodput medido** com volumes recebidos; reportar erro absoluto/relativo e causas.
6. Conferir logs de filas e verificar que enviar 100 msg/s não implica a mesma taxa de receções.
