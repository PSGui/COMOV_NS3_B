# B10 — Aproveitamento do contacto Wi-Fi com armazenamento no autocarro

**Aim original:** *Find out whether storing data on the bus makes better use of Wi-Fi contact at a stop.*

A pergunta operacional é: **quantos bytes úteis e mensagens únicas são recebidos no AP, dentro do prazo de 60 s, por cada segundo de associação Wi-Fi**, quando se conserva a informação no autocarro em FIFO, face ao envio imediato?

## Estado

- Matriz concluída: 2 velocidades × 3 paragens ×2 políticas ×10 runs = 120 execuções / 60 pares; baseline AP x=0 m.
- Ganhos de entrega FIFO face ao imediato: +30,774 pontos percentuais a 5 m/s e +33,325 pp a 15 m/s, sob o modelo configurado.
- A versão implementada expira mensagens na fila 60 s após geração. O plano inicial considerava também uma FIFO sem expiração: **não generalizar os resultados atuais para essa política alternativa**.
- O novo analisador e os ensaios de AP deslocado precisam de ser executados no WSL para produzir resultados; esta documentação descreve o protocolo e não antecipa resultados.

## 1. Métricas calculadas sobre os 120 conjuntos CSV existentes

O programa scripts/analyze_p2_contact.py lê summary, association e received de todas as runs, sem voltar a executar ns-3.

| Medida | Fórmula / interpretação |
|---|---|
| Taxa de entrega no prazo | 100 × mensagens únicas recebidas em até 60 s / 12000 geradas |
| Payload útil no AP | 1000 bytes × mensagens únicas recebidas |
| Duração associada | Soma dos períodos assoc→deassoc observados nos eventos MAC |
| **Goodput útil no prazo por contacto** | 8 × bytes úteis recebidos no prazo / duração associada, em Mbit/s |
| Goodput útil total por contacto | 8 × bytes úteis recebidos / duração associada, em Mbit/s |
| Janela ativa de receções | Instante da última receção menos primeira receção |
| Atraso | t_rx − t_gen, média, mediana, P95 e máximo **só para mensagens recebidas** |
| Custos da FIFO | Pico em bytes, overflow e expirações sem envio |

**Definição:** goodput por contacto é a quantidade de payload UDP útil recebida por segundo de associação. **Não mede airtime ocupado nem utilização PHY do canal Wi-Fi**. A PHY nominal é 6 Mbit/s mas tem overhead e retransmissões.

Os resultados serão guardados em:
- out/p2/contact_metrics_runs.csv — 120 linhas, por execução;
- out/p2/contact_metrics_summary.csv — médias de 12 grupos (seis cenários × duas políticas);
- out/p2/contact_metrics_pairs.csv — seis diferenças FIFO−imediato de entrega e goodput, IC95% emparelhados.

O P95 na tabela agregada é a **média dos P95 de cada run**, não um P95 global de todas as mensagens.

~~~bash
git pull
python3 scripts/test_p2_contact.py
python3 scripts/analyze_p2_contact.py --input-dir out/p2 --output-dir out/p2 --start-run 1 --end-run 10
python3 scripts/plot_p2_contact.py --input out/p2/contact_metrics_summary.csv --output-dir out/p2
~~~

O último comando gera out/p2/p2_contact_goodput_policies.png e out/p2/p2_fifo_delivery_delay.png.

Os erros de contabilidade ou CSV em falta provocam falha explícita, não imputação de valores.

## 2. Robustez geométrica — deslocação da posição do AP

O simulador ns-3 já possuía a opção --apX. O wrapper scripts/run_p2.sh aceita agora um sétimo parâmetro opcional: posição AP em −30, 0 ou +30 metros.

- Velocidade: 15 m/s; paragens: 0 e 30 s.
- AP em −30 m e +30 m, comparado com AP central de 0 m já simulado.
- Duas políticas: imediato e FIFO.
- Pacing FIFO: 2 ms; buffer: 4 MB; mesmo Wi-Fi e expoente 3.
- Primeira fase: run=1; **8 novas simulações**.

~~~bash
python3 scripts/run_p2_ap_robustness.py ../../ns-3 --start-run 1 --end-run 1 --skip-existing
~~~

Prefixos novos usam sufixos _apxm30 e _apxp30 para **não sobrescrever** a baseline. O script revalida a baseline com review_p2.py, revalida os casos novos e compara políticas com compare_p2.py. A tabela out/p2/ap_robustness_runs1-1.csv guarda entregas, alteração face ao AP central, goodput útil por contacto, tempo associado, overflow e expirações.

Deslocar o AP altera o perfil temporal de associação relativamente à paragem. **Não simula fading, shadowing, obstáculos ou interferências**.

## 3. Critérios de conclusão

- **Confirmado na baseline:** a FIFO aumenta as mensagens e bytes úteis entregues no prazo, mas pode aumentar o atraso e atingir 4 MB a 15 m/s.
- **A medir com os CSV existentes:** goodput útil por segundo de contacto e atraso das dez runs, com comparação emparelhada e IC95%.
- **A medir com simulações adicionais:** deslocação do AP e eventual perda do benefício na nova geometria.
- **Fora do âmbito da matriz principal:** afirmar ocupação real de canal, capacidade de uma rede rodoviária, ou comportamento de FIFO sem expiração.
