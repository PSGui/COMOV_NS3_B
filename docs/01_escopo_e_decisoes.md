# B10 — objetivo, questões e decisões

**Estado:** planeamento inicial; não existem resultados simulados. **Fonte normativa:** `Worksheet_B.pdf`, pp. 1–3 e 12 (B10).

## Problema científico

Um autocarro gera mensagens UDP enquanto se aproxima de uma paragem, permanece parado e segue viagem. A cobertura do AP é intermitente. Pergunta: **a retenção ao nível da aplicação melhora o volume de dados únicos entregues por passagem e a percentagem que chega dentro de 60 s, sem ocultar perdas ou atrasos?**

Hipóteses a testar, **não conclusões**:

- H1: um buffer pode permitir entregar mensagens geradas antes da associação; o benefício depende da janela efetiva de contacto;
- H2: velocidades elevadas e paragens curtas reduzem a oportunidade de descarregar o backlog;
- H3: FIFO pode entregar mais bytes, mas também mensagens demasiado antigas para cumprirem 60 s;
- H4 (complementar): a mudança de 802.11g/2,4 GHz para 802.11a/5 GHz, mantendo comparáveis os restantes parâmetros, pode alterar o alcance e os ganhos do buffer.

## Delimitação e fairness

- **12 configurações obrigatórias** = 2 velocidades (5, 15 m/s) × 3 tempos de paragem (0, 10, 30 s) × 2 políticas (imediata e buffer).
- Taxa = 100 mensagens/s, 1000 bytes **por mensagem UDP à aplicação**, durante a mesma janela de geração.
- **Imediata:** cada mensagem é submetida à socket quando gerada, sem fila adicional implementada na aplicação. Fila MAC/IP não é confundida com buffer de aplicação e deve ser registada.
- **Buffer FIFO:** se o AP não está associado, armazenar; após associação, enviar em ordem FIFO a um ritmo definido no piloto; novas mensagens entram na mesma fila. Capacidade proposta: 4 000 000 bytes de payload; **drop-newest** em overflow. O buffer não descarta automaticamente mensagens aos 60 s: a métrica considera entrega tardia.
- Dentro de cada par de políticas, conservar percurso, horários de geração, parâmetros PHY/MAC e entradas aleatórias externas.
- **Não** fixar "alcance Wi-Fi" no código por conveniência; é consequência do modelo de canal, da receção e do MAC.
- O ns-3 não é uma medição real de uma rua com obstáculos. Identificar sempre os mecanismos efetivamente simulados.

## Critérios de aceitação e limites

Métricas obrigatórias B10: bytes úteis únicos por passagem, entregas até 60 s, diferenças emparelhadas com IC95%, ocupação do buffer e receções alinhadas com associação, mensagens geradas/entregues/descartadas/pendentes, tempo útil e goodput durante contacto; robustez deslocando AP.

**O enunciado não impõe uma meta de 95% de entrega ao B10**. Os 95% referem-se ao intervalo de confiança das diferenças. Não criar uma meta de QoS arbitrária sem a rotular como hipótese adicional.

## Decisões pendentes (resolver na M2)

1. Versão instalada de ns-3; nomes exatos de PHY mode e trace sources para essa versão.
2. Sensibilidade/critério físico de receção e margens; confirmado por documentação e traces.
3. Expoente de propagação e cenário de robustez (sem alegar calibração empírica).
4. Ritmo de descarga do buffer: definido por piloto e depois congelado; não escolher 1 ou 2 ms por conveniência.
5. Fontes de aleatoriedade e streams; se pilotos forem determinísticos, não apresentar 10 repetições idênticas como evidência de incerteza.
6. Definição e identificação de perdas abaixo da aplicação e estado pendente.

## Sequência operacional

1. Cálculos independentes e tabela de parâmetros — **em preparação neste PR**.
2. Baseline de 1 AP + 1 STA móvel, UDP imediato, sem buffer e sem alteração artificial do estado de associação.
3. Primeiro piloto: trajetória, RSS, associação, receções, filas e contadores.
4. Implementar buffer FIFO, limites de memória, temporização e logging, validar casos unitários.
5. Pilotos de casos leve/crítico e congelar M2 (matriz, parâmetros, streams, duração e precisão).
6. Executar matriz 12 × ≥10 repetições emparelhadas, calcular IC95%.
7. Robustez: deslocação do AP; só depois comparação opcional 802.11a vs 802.11g.
8. Gerar figuras, relatório, README de reprodução e apresentação.

**Regra:** valores que dão resultados interessantes não são, por si só, fundamento para escolher parâmetros.
