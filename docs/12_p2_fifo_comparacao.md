# P2 — Comparação emparelhada: envio imediato vs FIFO de aplicação

**Estado atualizado (23/11/2026):** P2 compilou e executou no WSL (ns-3.48) para **5 m/s e paragem de 10 s**, nas duas políticas. Os 14 CSV enviados foram auditados independentemente: imediato 5620/12000 entregues no prazo, FIFO 9312/12000, ganho **+30,7667 pontos percentuais**, pico de 3,695 MB e zero overflow. [Relatório da auditoria](13_auditoria_p2_par_v5_stop10.md). Ainda faltam sensibilidade ao pacing, 15 m/s e repetições independentes.

## Objetivo

Quantificar quanto melhora a **entrega de mensagens geradas** quando a aplicação pode guardar mensagens enquanto o autocarro não está associado ao AP, escoando-as posteriormente pela ligação Wi-Fi durante a paragem e passagem.

A implementação usa **um só cenário C++** para as duas políticas, com a mesma geometria, PHY/MAC, carga, janelas, observação e configuração RNG. Só o comportamento da aplicação difere.

## Políticas

### A. Immediate — sem buffer

1. Geração uniforme de 100 mensagens/s em [10,130) s.
2. Se STA não estiver associada: registar \`no_association\` e não chamar \`SendTo\`.
3. Se STA estiver associada: chamar \`SendTo\` imediatamente, sem fila de aplicação.
4. Contabilizar separadamente socket aceite/rejeitada e receção no AP.

A implementação no P2 deve reproduzir o comportamento do P1 para o mesmo seed/run. O resultado anterior de P1 foi 5620 entregas em 12000 geradas; tratar como referência **a comparar**, não como garantia de igualdade se forem descobertas alterações de configuração.

### B. FIFO de aplicação — limitado

1. Cada mensagem gerada é **enfileirada na aplicação**, associada ou não, respeitando a ordem de geração.
2. Capacidade: **4 000 000 bytes de payload** = 4000 mensagens de 1000 bytes. A fila representa os 1000 bytes por mensagem, apesar de guardar internamente apenas ID e instante de geração como metadados compactos; o payload completo é reconstruído no envio.
3. Fila cheia: **drop-newest**, ou seja, a mensagem nova é descartada, sem remover a mais antiga.
4. Prazo máximo: **60 s desde o instante de geração**. As mensagens que continuam na fila ao atingirem 60 s expiram e são descartadas. Um callback por mensagem garante essa expiração mesmo sem associação. A receção de um datagrama enviado antes do limite mas recebido depois é marcada tardia.
5. Só escoar com \`StaWifiMac::IsAssociated() == true\`. A associação MAC não garante qualidade do sinal, pelo que todos os envios e receções continuam registados separadamente.
6. Enviar **no máximo um datagrama por 2 ms** enquanto existem mensagens. O espaçamento aplica-se mesmo quando a fila fica momentaneamente vazia. Um \`SendTo\` com retorno 1000 remove a mensagem da FIFO mas não prova que chegou ao AP.
7. No envio, os 1000 bytes de payload contêm 8 bytes para o ID, 8 bytes para o timestamp da geração e 984 bytes restantes.

### Justificação provisória dos parâmetros

- 4 MB = 4000 ×1000 bytes = **40 s de geração** sem transmissões.
- Com v=5 m/s, P1 observou associação aos 46,94 s; a geração começa aos 10 s. Até à associação há aproximadamente **36,94 s** de mensagens acumuladas, abaixo dos 40 s de capacidade. Este valor de buffer foi definido antes do teste FIFO.
- Pacing de 2 ms ⇒ teto de **500 mensagens/s** e **4 Mbit/s de payload útil**. É inferior à taxa PHY fixa de 6 Mbit/s, mas overhead MAC/PHY, ACK, backoff e headers podem tornar esta carga excessiva. **Não confundir teto de envio da aplicação com capacidade útil medida**. A escolha será verificada no piloto e testada também com pacing de 3 ms como robustez, caso necessário.
- O limiar de deteção de preâmbulo Wi-Fi usado por omissão no ns-3.48 é −82 dBm, e o P1 observou a última receção com potência prevista perto de −81,997 dBm. Este valor resulta do modelo do simulador; não é um valor medido numa estrada.

## Métricas a reconciliar

Para **immediate**:

~~~
N_generated = N_no_association + N_socket_rejected + N_socket_accepted
~~~

Para **FIFO**:

~~~
N_generated = N_enqueued + N_buffer_overflow
N_enqueued = N_buffer_expired + N_buffer_sent_attempts + N_buffer_remaining
N_buffer_sent_attempts = N_socket_rejected + N_socket_accepted
~~~

Para ambas:

~~~
N_socket_accepted = N_received_unique + N_accepted_not_observed
N_received_unique = N_received_on_time + N_received_late
P_on_time = N_received_on_time / N_generated
~~~

As diferenças **socket aceitou / AP não recebeu** não têm ainda causa MAC/PHY identificada. O UDP não oferece entrega garantida. A FIFO também não implementa retries de aplicação após \`SendTo\` aceite — isto evita tratar o armazenamento como uma retransmissão fiável não exigida no B10.

## Ficheiros de cada execução

A execução produz, com prefixo próprio:

- \`_generated.csv\`: todas as mensagens, instante de geração, distância, associação e disposição inicial (no FIFO \`enqueued\` ou \`buffer_full\`).
- \`_sent.csv\`: ID, instante de geração, instante de chamada a \`SendTo\`, idade no envio, retorno da socket.
- \`_received.csv\`: receções efetivas e tempos no AP.
- \`_association.csv\`: eventos reais MAC.
- \`_mobility.csv\`: amostras de percurso e potência teórica.
- \`_buffer.csv\`: eventos \`enqueued\`, \`drop_newest\`, \`expired\`, \`send_accepted\`, \`send_rejected\`; ocupação após cada evento.
- \`_summary.csv\`: reconciliação, capacidade, pico de ocupação, pacing e valores PHY do cenário.
- \`_analysis.json\`: resultado da verificação independente \`review_p2.py\`.

O validador reconstrói a FIFO evento a evento, verifica a **ordem efetiva de transmissão**, a capacidade, as expirações e os contadores. Um teste Python sintético também cobre a expiração em ausência de associação, sem depender do simulador.

## Primeiro par controlado no WSL

Após integração do PR:

~~~bash
cd ~/COMOV/Project_B/COMOV_NS3_B
git pull

# Testes do validador, independentes do simulador
python3 scripts/test_p2_validation.py

# 1. Baseline com o mesmo programa e os mesmos parâmetros
bash scripts/run_p2.sh ../../ns-3 immediate 5 10

# 2. FIFO de 4 MB, espaçamento de 2 ms
bash scripts/run_p2.sh ../../ns-3 fifo 5 10

# 3. Comparação e gráficos
python3 scripts/compare_p2.py \
  --immediate-prefix out/p2/v5_stop10_run1_immediate \
  --fifo-prefix out/p2/v5_stop10_run1_fifo

python3 scripts/plot_p2.py \
  --immediate-prefix out/p2/v5_stop10_run1_immediate \
  --fifo-prefix out/p2/v5_stop10_run1_fifo \
  --output-dir out/p2
~~~

**Primeiro critério:** o P2/immediate deve produzir 12000 geradas e valores de receção compatíveis com o P1 para seed=1/run=1. Se a comparação não coincidir, identificar alterações antes de concluir qualquer ganho de FIFO.

**Segundo critério:** toda a contabilidade de FIFO tem de fechar. A melhoria esperada é hipótese, não resultado assegurado; pacing pode induzir congestionamento MAC apesar de a carga nominal ser inferior aos 6 Mbit/s PHY.

**Terceiro critério:** os gráficos criados a partir dos CSV devem mostrar, ao longo do tempo, o crescimento/escoamento da fila, o momento de associação e as receções UDP.

### Pacing alternativo — só como controlo

~~~bash
bash scripts/run_p2.sh ../../ns-3 fifo 5 10 1 3
~~~

A execução alternativa cria um prefixo separado \`out/p2/v5_stop10_run1_fifo_pace3\`, evitando sobrescrever resultados de 2 ms.

## Validação pendente antes dos 12 cenários

1. Compilação P2 em ns-3.48, sem alterações manuais fora do repositório.
2. Validador Python aprovar ambas as políticas.
3. Inspeção da FIFO temporal e das suas expirações com os CSV reais.
4. Comparação com a baseline P1 já aprovada.
5. Inspeção dos datagramas aceites mas não recebidos, sem atribuição automática a perda PHY.
6. Definição final do pacing antes de lançar a matriz de 12 configurações.
7. Só depois planeamento de 10 repetições por configuração, runs emparelhadas e IC95%.

**Limitação para inferência estatística:** a baseline de propagação é determinística e o número de runs por configuração ainda é 1. Para intervalos de confiança científicos, planear explicitamente as fontes de aleatoriedade e o emparelhamento dos streams RNG, além de aumentar as repetições.

## Primeiro par executado — referência e leitura crítica

Resultados completos, algoritmos de contabilidade e 14 CSV verificados no [relatório de auditoria P2](13_auditoria_p2_par_v5_stop10.md). A FIFO esvaziou-se em t=56,174678770 s, **antes da paragem em t=70 s**, e recuperou 3692 mensagens anteriores à associação. Este facto demonstra o potencial do buffer no cenário simulado, mas não permite inferir que a paragem seja desnecessária; é preciso comparar 0, 10 e 30 s. Os 2 ms de pacing e os 4 MB continuam hipóteses experimentais e exigem testes de robustez.
