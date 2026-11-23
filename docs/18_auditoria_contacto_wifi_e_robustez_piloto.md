# B10 — Auditoria do aproveitamento do contacto Wi-Fi e robustez geométrica

**Data:** 23/11/2026. **Aim:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.*

**Fontes efetivamente inspecionadas:** CSV individuais agregados `contact_metrics_runs.csv` (120 linhas), `contact_metrics_summary.csv` (12 linhas), `contact_metrics_pairs.csv` (6 linhas) e piloto de AP deslocado `ap_robustness_runs1-1.csv` (8 linhas), enviados pelo grupo. Dois PNGs de goodput e atraso foram também apresentados. Esta auditoria verificou independentemente aritmética do goodput, emparelhamento dos 10 runs por condição, integridade de prazo de entrega e IC95% com Student-t (`scipy.stats.t.interval`), comparando com os resultados do CSV.

## 1. Definição operacional do objetivo

A **melhoria no aproveitamento do contacto** foi medida como o aumento de *payload UDP útil e único recebido no AP dentro de 60 s desde geração por segundo de associação MAC*. Para cada execução:

```
G_contact_on_time [Mbit/s] =
    8 * 1000 * N_unique_received_on_time / (1e6 * T_MAC_associated_s)
```

O denominador é **tempo em que a STA esteve associada**, e não tempo de efetiva ocupação da PHY. Portanto **não é uma medição de airtime, de utilização do canal rádio, nem do throughput máximo PHY**. No fim do contacto pode permanecer estado MAC associado sem receção de datagramas UDP. O período entre a primeira e última receção é registado separadamente, mas também não equivale a airtime.

Matriz analisada: 5/15 m/s × paragens 0/10/30 s × envio imediato/FIFO ×10 runs = 120 execuções, 60 pares. Mesmo percurso, associação e geração dentro de cada par. Média de 10 goodputs por política e intervalo de confiança de Student-t sobre as **10 diferenças emparelhadas**, não IC sobre taxa individual.

## 2. Goodput no prazo por segundo de associação

| Velocidade | Paragem | Imediato (Mbit/s) | FIFO (Mbit/s) | Ganho (Mbit/s) | IC95% do ganho | Razão FIFO/imediato |
|---|---:|---:|---:|---:|---|---:|
| 5 m/s | 0 s | 0,783505 | 1,409634 | +0,626129 | [0,625841; 0,626417] | 1,80× |
| 5 m/s | 10 s | 0,786052 | 1,302466 | +0,516414 | [0,516114; 0,516713] | 1,66× |
| 5 m/s | 30 s | 0,789888 | 1,172639 | +0,382750 | [0,382589; 0,382911] | 1,48× |
| 15 m/s | 0 s | 0,752677 | 2,711649 | +1,958973 | [1,955234; 1,962711] | 3,60× |
| 15 m/s | 10 s | 0,770519 | 1,985307 | +1,214787 | [1,213548; 1,216027] | 2,58× |
| 15 m/s | 30 s | 0,783266 | 1,473728 | +0,690462 | [0,690014; 0,690910] | 1,88× |

**Interpretação do aim:** a FIFO entrega mais volume útil por cada segundo de associação em **todos os seis cenários**. A maior melhoria relativa ocorre em passagem rápida sem paragem (15 m/s, 0 s): aproximadamente **3,60×** o goodput de envio imediato. O benefício não representa maior capacidade de rádio; resulta da transmissão de um backlog de mensagens previamente acumuladas quando surge contacto.

O goodput médio da FIFO **diminui** quando a duração da paragem aumenta (por exemplo, 15 m/s: 2,712→1,474 Mbit/s), ainda que **o volume total entregue aumente**. Depois de escoar o backlog, o sistema fica limitado à geração de novos dados a 0,8 Mbit/s de payload. O denominador (tempo de associação) também cresce. Assim, **não concluir que parar mais tempo prejudica as entregas ou a utilidade do contacto**.

O ganho de entrega relativamente às 12 000 mensagens geradas mantém-se entre paragens de cada velocidade: +30,774 pp a 5 m/s e +33,325 pp a 15 m/s. Esta invariância é própria desta geometria e modelo, não garantia geral.

## 3. Custos em atraso — estatísticas das 10 runs

| Velocidade | Paragem | Atraso médio FIFO (s) | Média dos P95 FIFO por run (s) | Atraso médio imediato (ms) |
|---|---:|---:|---:|---:|
| 5 m/s | 0 s | 10,253 | 33,600 | 1,484 |
| 5 m/s | 10 s | 9,152 | 33,200 | 1,484 |
| 5 m/s | 30 s | 7,534 | 32,400 | 1,484 |
| 15 m/s | 0 s | 26,986 | 50,132 | 1,487 |
| 15 m/s | 10 s | 22,857 | 49,732 | 1,485 |
| 15 m/s | 30 s | 17,502 | 48,932 | 1,484 |

As médias e os P95 dizem respeito **às mensagens recebidas**, não às descartadas. Todos os datagramas únicos recebidos nos 120 registos tinham `n_unique_delivered == n_on_time`; o sistema implementado **expira mensagens FIFO aos 60 s ainda em fila**, de modo que estas execuções não testam uma política sem expiração que envie mensagens atrasadas. A coluna `latency_p95_s_mean` é a **média dos P95 por run**, e não o P95 de todas as receções agrupadas.

**Conclusão:** maior entrega é obtida à custa de atraso por espera na fila, chegando a cerca de 27 s de média e 50 s na média dos P95 para 15 m/s, 0 s de paragem. Para mensagens cujo valor dependa de baixa latência, a estratégia FIFO necessita de uma política de prioridade/expiração adequada; não considerar apenas a percentagem entregue.

## 4. Robustez geométrica AP ±30 m — apenas um piloto (run=1)

Condições: v=15 m/s; paragem=0 ou 30 s; duas políticas; AP central x=0 m e deslocado x=−30 ou +30 m. O CSV inclui 8 linhas — duas políticas × duas paragens × duas posições deslocadas. Os quatro cenários de AP central foram reutilizados, não repetidos.

| Paragem | AP x | Imediato no prazo | FIFO no prazo | Ganho FIFO | Goodput imediato | Goodput FIFO |
|---|---:|---:|---:|---:|---:|---:|
| 0 s | −30 m | 1538 | 5535 | +3997 | 0,752 | 2,705 |
| 0 s | 0 m (ref.) | 1533 | 5530 | +3997 | 0,754 | 2,721 |
| 0 s | +30 m | 1537 | 5534 | +3997 | 0,752 | 2,708 |
| 30 s | −30 m | 4538 | 8535 | +3997 | 0,783 | 1,472 |
| 30 s | 0 m (ref.) | 4533 | 8530 | +3997 | 0,784 | 1,475 |
| 30 s | +30 m | 4537 | 8534 | +3997 | 0,783 | 1,473 |

Goodput útil no prazo em Mbit/s. **Não comparar as pequenas diferenças de uma única run como significativas estatisticamente.** Com AP deslocado, as duas políticas ganham mais quatro ou cinco receções em relação à referência, mantendo o **ganho adicional FIFO de 3997 mensagens**. O efeito no goodput é pequeno e até ligeiramente negativo, devido ao aumento discreto do tempo de associação.

No caso 15 m/s e paragem=30 s, a posição do AP altera **muito mais as perdas por buffer** do que o número de mensagens entregues:

| AP x | Overflow FIFO | Expirações FIFO |
|---|---:|---:|
| −30 m | 1034 | 2329 |
| 0 m | 1239 | 2135 |
| +30 m | 1435 | 1930 |

Isto evidencia sensibilidade do *momento* de início/fim de associação à geração e ao enchimento do buffer. Não concluir que as posições deslocadas são equivalentes em todas as métricas só porque o número de mensagens recebidas quase não mudou.

**Limite científico:** deslocar AP ±30 m num modelo log-distance homogéneo e determinístico é uma **robustez geométrica restrita**. Não representa obstáculos, multipercurso, variabilidade urbana nem colisões com outros utilizadores. Com n=1 não há IC95% para este teste de robustez.

## 5. Validações independentes efetuadas

- 120 linhas em `contact_metrics_runs.csv` sem valores ausentes e sem duplicação de (velocidade, paragem, política, run); 10 runs para cada um dos 12 cenários.
- Todas as 120 execuções têm 12 000 mensagens geradas, `n_unique_delivered == n_on_time` e atraso máximo observado inferior a 60 s.
- Identidade entre a fórmula do goodput e as colunas do CSV por run; todos os tempos associados coincidem entre políticas emparelhadas.
- Médias por grupo consistentes com os 120 registos; diferenças e IC95% emparelhados de goodput recalculados com Student-t a partir dos dez registos e coincidentes com `contact_metrics_pairs.csv`.
- Em `ap_robustness_runs1-1.csv`, a diferença FIFO-imediato no prazo manteve-se em 3997 mensagens nos quatro pares deslocados; o efeito sobre overflow e expiração foi separado da entrega.
- Os dois PNGs de goodput e atraso representam as séries presentes nos CSV; representam goodput de aplicação por associação, e não utilização PHY do canal.

## 6. Decisão metodológica seguinte

**Já está respondida a questão do enunciado para o modelo de referência:** armazenar no autocarro permite aproveitar melhor as oportunidades de contacto Wi-Fi, entregando mais payload útil por segundo de associação e mais mensagens no prazo. A resposta requer sempre a ressalva do atraso e da capacidade finita.

Antes do relatório final, discutir a abrangência da “robustez”: um piloto AP ±30 m mostra estabilidade do benefício sob deslocação geométrica pequena; não é validação em canal estocástico real. Para uma declaração quantitativa de robustez, executar várias runs nos pontos deslocados ou usar um modelo de propagação variado, sem alterar a matriz já congelada.

### Ficheiros de origem e hashes SHA-256

| Ficheiro | SHA-256 |
|---|---|
| `contact_metrics_runs.csv` | `4e77205f38404ac9c7f87282f97d3699be1606dd4055f1d943c27d4e0a6e888b` |
| `contact_metrics_summary.csv` | `0c03fd3ad03ba91766f17339c3fa0ae377772566e3f306613fedbf08dca23993` |
| `contact_metrics_pairs.csv` | `0ec007e1ae1b4d2fa9463263aa943a8a4de21ae58936017e220938524d9e08cd` |
| `ap_robustness_runs1-1.csv` | `cd193df868fd8b90f5f13452ec70530513a189c2a269eff4a459dabdd70404b1` |
