# P2 — Auditoria dos 14 CSV do par de pilotos: imediato vs FIFO

**Data:** 23/11/2026. **Cenário:** ns-3.48, IEEE 802.11g/ERP-OFDM, f=2,412 GHz, Pt=20 dBm, modelo log-distance n=3, v=5 m/s, paragem de 10 s, RNG seed=1/run=1. Geração [10,130) s: **100 mensagens/s × 1000 bytes = 12 000 mensagens**; limite de entrega 60 s desde geração; observação até t=200 s.

**Proveniência:** auditoria independente dos **14 CSV reais carregados pelo grupo** (sete para cada política: association, buffer, generated, mobility, received, sent, summary). Os CSV brutos **não são guardados no repositório público** e permanecem no diretório local out/p2/.

**Estado:** compilação/execução do P2 demonstrada pelos CSV. A análise independente dos ficheiros validou a conservação das mensagens, sequência FIFO, capacidade, tempos e resultados. Repetições estatísticas e robustez **pendentes**.

## 1. Comparabilidade do par

Os CSV indicam precisamente a mesma configuração em ambas as políticas:

- v=5 m/s, s=10 s, AP em x=0 m, potência=20 dBm, n=3, IEEE 802.11g, frequência 2,412 GHz;
- seed 1, run 1;
- associação em **t=46,940678770 s**, x=−115,296606 m, distância 3D 115,306363 m;
- desassociação em **t=104,140776386 s**, x=+120,703882 m, distância 3D 120,713202 m;
- duração associada: **57,200097616 s**;
- 12 000 mensagens e instantes/posições de geração correspondentes.

Traços de associação dos dois cenários coincidem exatamente. As posições e a potência modelada coincidem até à resolução numérica dos CSV; pequenas diferenças de **1×10⁻⁹** em algumas colunas de distância/potência decorrem de arredondamento e não são alterações materiais de percurso. O comparador foi atualizado para verificar igualdade numérica com tolerância de 10⁻⁶ em vez de comparar strings formatadas.

## 2. Contagem de mensagens e entregas

| Medida | Imediato | FIFO |
|---|---:|---:|
| Geradas | 12 000 | 12 000 |
| Descartadas na aplicação sem associação | 6 280 | 0 |
| Armazenadas na FIFO ao gerar | 0 | 12 000 |
| Descartadas por overflow | — | 0 |
| Expiradas em fila antes de enviar | — | 2 585 |
| Aceites pela socket UDP | 5 720 | 9 415 |
| Rejeitadas pela socket | 0 | 0 |
| Recebidas únicas no AP | 5 620 | 9 312 |
| Recebidas dentro dos 60 s | 5 620 | 9 312 |
| Recebidas tarde / duplicadas | 0 / 0 | 0 / 0 |
| Aceites na socket, não observadas no AP | 100 | 103 |
| Pendentes no buffer ao fim | — | 0 |
| Payload útil entregue (MB decimais) | 5,620 MB | 9,312 MB |
| **Entrega no prazo / geradas** | **46,8333%** | **77,6000%** |

**Ganho neste par:** **3692 mensagens adicionais**, **+30,7667 pontos percentuais** de entrega no prazo. Equivale a **+65,694%** de mensagens entregues relativamente à política imediata.

Comparação da taxa de receção **condicionada à aceitação pela socket**: 5620/5720 = **98,2517%** (imediato) e 9312/9415 = **98,9060%** (FIFO). Estes denominadores são diferentes e a taxa não representa o desempenho global da política: a grande vantagem da FIFO vem de recuperar mensagens geradas *sem associação*.

### Conservação exata

**Imediato:** 12000 = 6280 descartadas por ausência de associação + 5720 aceites na socket. Das 5720 aceites, 5620 chegaram ao AP e 100 não foram observadas até t=200.

**FIFO:** 12000 = 12000 enfileiradas + 0 overflow; 12000 = **9415 aceites na socket + 2585 expiradas na FIFO + 0 pendentes**. Das 9415 aceites, 9312 chegaram ao AP e 103 não foram observadas.

A auditoria percorreu os **24000 eventos da fila FIFO**: 12000 enqueue + 9415 send_accepted + 2585 expired; a remoção no envio e na expiração respeitou a ordem FIFO, ocupação e contadores. Não houve mensagens expedidas após 60 s na fila.

## 3. Onde se ganhou exatamente

- **Antes da primeira associação:** geradas **3695 mensagens** (IDs 0–3694, t=10,00–46,94 s). A política imediata descartou-as; a FIFO recuperou **3692**, não recebendo os IDs **3–5** embora tivessem sido aceites pela socket.
- **Durante a associação:** geradas **5720 mensagens** (IDs 3695–9414). Em **ambas as políticas**, **5620** chegaram ao AP.
- **Após a desassociação:** geradas **2585 mensagens** (IDs 9415–11999, t=104,15–129,99 s). A política imediata descartou-as; a FIFO guardou-as, mas **não surgiu nova associação**, pelo que todas expiraram na fila ao atingir 60 s (primeira em t=164,15 s, última em t=189,99 s).

Logo, a diferença entre as políticas é integralmente explicada pelas **3692 mensagens pré-associação recuperadas**. Não houve melhoria de entrega observada para mensagens geradas durante a associação, neste caso.

### Mensagens aceites na socket mas não recebidas

- **Imediato:** IDs 9315–9414 (100 mensagens consecutivas), geradas entre 103,15 e 104,14 s.
- **FIFO:** IDs 3–5 (**três** mensagens durante o início do escoamento em t≈46,947–46,951 s) e IDs 9315–9414 (100). Não inventar a causa dos três datagramas iniciais; falta instrumentação PHY/MAC para distinguir perda, retransmissões e descartes de fila.
- O limite de 100 datagramas finais coincide com a janela após a última entrega (ID 9314, chegada em 103,141478386 s) e antes da desassociação (104,140776386 s). O P1 já sugerira associação mantida temporariamente após perda de capacidade de receção, compatível com o limiar default de deteção de preâmbulo de −82 dBm do modelo ns-3.48. **Não equiparar aceitação por SendTo com êxito PHY.**

## 4. Ocupação, escoamento e relação com a paragem

- FIFO inicia armazenamento em t=10 s.
- **Ocupação máxima:** 3 695 000 bytes = **3,695 MB**, em t=46,94 s, antes de a STA associar.
- Capacidade configurada: **4 000 000 bytes**. Utilização máxima **92,375%**. Margem: **305 000 bytes = 305 mensagens**.
- Primeiro envio FIFO: **t=46,940678770 s**, com ID 0, gerado em t=10 s.
- Espaçamento de escoamento: **2 ms**, até 500 mensagens/s = 4 Mbit/s de payload da aplicação; de 47 a 55 s, observam-se 500 mensagens recebidas por segundo em cada segundo completo.
- **Primeiro instante de fila vazia durante associação:** t=**56,174678770 s**, cerca de **9,234 s** após associar.
- O autocarro só pára de t=70 a 80 s. A FIFO **já estava vazia 13,825 s antes da paragem**. A partir daí, as mensagens novas são enviadas à medida que chegam (100/s).
- Após t=104,14 s, não há nova associação. A FIFO cresce até armazenar 2585 mensagens; termina em zero quando todas expiram até 189,99 s.

**Interpretação física importante:** nesta configuração, os benefícios do armazenamento ocorreram sobretudo **na aproximação**, antes da paragem. Não se pode concluir a partir de um único caso que a duração da paragem não importa. É necessário comparar s=0,10,30 s para a mesma velocidade e política.

O escoamento inicialmente projetado pode ser interpretado por uma taxa de serviço nominal de 500/s e geração de 100/s: a fila pré-existente de 3695 mensagens reduzir-se-ia aproximadamente a 400 mensagens/s, prevendo esvaziamento em ≈9,24 s. O valor observado foi **9,234 s**, consistente com o cálculo. Essa taxa é de **submissão de aplicação**, não a capacidade PHY utilizável do canal.

## 5. Compromisso entre entrega e atraso

| Estatística de atraso das mensagens recebidas | Imediato | FIFO |
|---|---:|---:|
| Média | **1,485 ms** | **9,151 s** |
| Mediana | **1,478 ms** | **1,478 ms** |
| Percentil 95 | **1,478 ms** | **33,194 s** |
| Máximo | **11,758 ms** | **36,952 s** |

A FIFO recuperou mensagens antigas. Os atrasos das **3692 mensagens recuperadas geradas antes da associação** têm média de **22,154 s**. As mensagens geradas durante a associação também podem ficar temporariamente atrás do backlog, pelo que não se deve assumir atraso baixo apenas porque foram geradas já associadas.

**Todas as 9312 mensagens recebidas pela FIFO cumpriram o prazo de 60 s**, mas a melhoria no volume entregue não foi gratuita: houve aumento substancial dos atrasos de cauda.

As métricas de atraso referem-se exclusivamente às mensagens que chegaram ao AP; o atraso de mensagens não recebidas não é observável.

## 6. Estado de validação e próximos ensaios

- **Validação concluída:** duas execuções compatíveis, integridade e correspondência do cenário, conciliação de contadores, replay FIFO, expirações, entregas e percentis de atraso auditados com os CSV reais.
- **Por confirmar:** causas exatas dos três datagramas iniciais e 100 finais, capacidade MAC/PHY em situações de congestão, alcance em ambientes não calibrados.
- **Sem inferência estatística:** apenas **run=1**, propagação determinística, sem estudo independente das fontes de aleatoriedade. Não apresentar IC95% deste par.

Próximos controlos **antes da matriz 12×10**:

1. FIFO com pacing de **3 ms**, mantendo v=5 m/s e paragem=10 s, para verificar sensibilidade a taxa de escoamento e atrasos.
2. Caso v=15 m/s, paragem=10 s, para testar efetivamente a capacidade de 4 MB e expirações de mensagens anteriores à associação.
3. Após validar estes pilotos, definir e congelar pacing e fontes de aleatoriedade por configuração antes das 10 repetições e diferenças emparelhadas com IC95%.

## Reproduzir a análise sem simular novamente

Na raiz do repositório, depois de atualizar os scripts:

~~~bash
git pull
python3 scripts/review_p2.py --prefix out/p2/v5_stop10_run1_immediate --require-contact
python3 scripts/review_p2.py --prefix out/p2/v5_stop10_run1_fifo --require-contact
python3 scripts/compare_p2.py \
  --immediate-prefix out/p2/v5_stop10_run1_immediate \
  --fifo-prefix out/p2/v5_stop10_run1_fifo \
  --output-json out/p2/v5_stop10_run1_pair_analysis.json
~~~

O comparador mais detalhado confirma que os CSV de associação, mobilidade e geração constituem um par válido; imprime os grupos exatos de IDs aceites mas não recebidos, quantifica as mensagens recuperadas antes da associação e o instante em que a FIFO se esvazia, além de médias e percentis de atraso.

### Identificadores dos ficheiros de auditoria

Hashes SHA-256 dos ficheiros CSV mais importantes:

| Ficheiro | SHA-256 |
|---|---|
| fifo_summary.csv | \`1bc4427de271fea321aab2e8a545710092e3a291f219ae19a95ba2928a134a3c\` |
| immediate_summary.csv | \`d7a438c00d2edfd4120c5e47cd2f190c4638dc63d619d61104e33bda327c049c\` |
| fifo_buffer.csv | \`2d09126e056928d415b723ca697b5f4e5f85cb6b19ccac4fc47919d2087afc15\` |
| fifo_received.csv | \`4559d09a92e07a65db3bde84375fdfa9301e7c86ff0dd1cc863194fe2c039bab\` |
| immediate_received.csv | \`c394608e382895e8d088fa33bb52439ecf1896a9e7afab6b481d2fec3f73c800\` |
