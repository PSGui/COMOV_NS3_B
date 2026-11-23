# P1 — primeira execução do piloto (5 m/s, paragem 10 s)

**Data:** 23/11/2026. **Fonte:** output do terminal WSL fornecido pelo grupo; os ficheiros CSV individuais **ainda não foram inspecionados nem validados integralmente**.

## Configuração

Simulador ns-3.48, infraestrutura IEEE 802.11g em 2,412 GHz, taxa ERP-OFDM 6 Mbit/s, potência TX 20 dBm, propagação log-distance n=3 e d0=1m; autocarro a 5 m/s com paragem de 10 s a iniciar em t=70 s. Janela de geração [10,130) s, 100 mensagens UDP/s com payload de 1000 bytes e deadline de 60 s. Envio imediato com descarte de aplicação sem associação.

## Output observado

| Variável | Valor |
|---|---:|
| Mensagens geradas | 12000 |
| Descartadas na aplicação sem associação | 6280 |
| Aceites pela socket UDP | 5720 |
| Rejeitadas pela socket UDP | 0 |
| Mensagens únicas recebidas no AP | 5620 |
| Recebidas dentro dos 60 segundos | 5620 |
| Recebidas fora do prazo | 0 |
| Aceites pela socket mas não observadas no AP até t=200 s | 100 |
| Eventos de associação / desassociação | 1 / 1 |
| Tempo associado reportado | 57,2001 s |

Métricas calculadas a partir do output:

- Entrega dentro do prazo relativa às mensagens geradas: 5620 / 12000 = **46,8333%**.
- Entrega observada relativa às mensagens aceites pela socket: 5620 / 5720 = **98,2517%**.
- Bytes úteis de aplicação recebidos: 5620 × 1000 = **5 620 000 bytes**.
- Bytes úteis gerados: 12000 × 1000 = **12 000 000 bytes**.

**Estas duas taxas têm denominadores diferentes; não são intercambiáveis.** O sucesso de SendTo significa aceitação pela socket UDP, não transmissão PHY, não ACK MAC e não receção.

## Resultado do validador independente

A simulação **compilou, executou até ao fim e fechou a contabilidade interna C++**. O script de análise parou com:

~~~
KeyError: 'unique_received'
~~~

**Causa:** o CSV de resumo escrito pelo C++ usa a coluna received_unique. O dicionário do validador Python usava unique_received. A correção é exclusivamente no verificador: renomear a chave para received_unique, mantendo a coluna CSV existente.

Foi adicionado um teste sintético com associação, 10 datagramas aceites, 8 entregues e 2 não observados, para que o problema seja detetado automaticamente em alterações futuras.

**Estado:** resultados C++ preliminares, execução simulada confirmada, auditoria dos CSV individuais **pendente de reexecução do verificador corrigido**.

### Passo necessário após integração da correção

Na pasta do repositório COMOV_NS3_B:

~~~bash
git pull
python3 scripts/test_p1_validation.py
python3 scripts/review_p1.py --prefix out/p1/v5_stop10_run1 --require-contact
python3 scripts/plot_p1.py --prefix out/p1/v5_stop10_run1
~~~

**Não é necessário voltar a correr o ns-3**. Os CSV da simulação já existem em out/p1/; é suficiente validar e visualizar os ficheiros conservados.

## Próximas verificações científicas

1. Ler os instantes exatos de Assoc/DeAssoc no CSV e comparar com os momentos de entrega UDP.
2. Inspecionar os 100 IDs aceites mas não observados: estão concentrados antes/depois da janela útil? São descargas tardias de filas? Não decidir a causa sem logs MAC/PHY.
3. Confirmar a distância e a potência modelada no instante da primeira e última receções; não interpretar a distância de desassociação como limiar universal de cobertura.
4. Só depois testar as outras velocidades e paragens, mantendo a política e o horizonte.
