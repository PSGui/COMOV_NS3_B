# Parâmetros do B10 — rastreabilidade

**Fonte:** enunciado B10 da ficha (p. 12); secções comuns nas pp. 1–3. Configuração editável: [`params/reference.json`](../params/reference.json).

Legendas: **OBR.** = imposto; **PROP.** = proposto por nós e ainda não validado; **PILOTO** = decidir após testes; **DER.** = calculado, não configurado.

| Elemento | Valor / política | Estado | Justificação / validação |
|---|---:|:---:|---|
| AP e autocarro | 1 AP fixo + 1 STA móvel | OBR. | B10 |
| Velocidade de aproximação | 5 e 15 m/s | OBR. | B10 |
| Paragem | 0, 10, 30 s | OBR. | B10 |
| Políticas | imediato; FIFO com buffer | OBR. | B10 |
| Taxa geração | 100 mensagens/s | OBR. | B10 |
| Payload UDP | 1 000 bytes/mensagem | OBR. | B10; ID + t_geração **incluídos** nos 1000 bytes |
| Prazo de entrega | 60 s após geração | OBR. | B10 |
| Configurações | 12 | DER. | 2 × 2 × 3 |
| Repetições iniciais | ≥10/configuração | OBR. | Método comum |
| IC diferenças | 95%, emparelhado | OBR. | Método comum |
| Norma referência | 802.11g, 2,412 GHz, 20 MHz | PROP. | Ensaiar como baseline; não é uma exigência de B10 |
| Estudo complementar | 802.11a, 5,180 GHz, 20 MHz | PROP. | Comparação de bandas **e** normas, não isolar apenas efeito MAC |
| PHY | taxa fixa 6 Mbit/s | PROP. | Modo OFDM compatível a confirmar na versão ns-3 |
| Potência TX | 20 dBm | PROP. | Exemplo inicial para orçamento rádio, verificar viabilidade/restrições |
| Antenas | Gt=Gr=0 dBi, perdas de sistema=0 dB | PROP. | Simplificação explicitada, não ganho medido |
| AP/STA altura | 4,0 / 2,5 m | PROP. | Separação vertical 1,5 m em trajetória 3D |
| Modelo propagação | log-distance (d0=1m; n=3) | PROP. | Expoente não calibrado; usar referência FSPL à frequência selecionada |
| Shadowing/fading | ausente na baseline | PROP. | Limitação; robustez futura separada |
| Sensibilidade e margem | por definir | PILOTO | Não confundir threshold RSS com taxa de entrega real |
| Associação | gerida por StaWifiMac | OBR. | Registar associação/desassociação; não forçar o instante |
| Tempo de início da paragem | t=70 s | PROP. | Alinhamento temporal entre experiências |
| Geração de mensagens | [10,130) s | PROP. | 120 s comuns; warm-up [0,10) s |
| Observação final | t=200 s | PROP. | +70 s para concluir prazo de 60 s de toda a janela de geração |
| Tráfego acumulado | 12 000 mensagens; 12 MB | DER. | 120 ×100; 12 000 ×1 000 |
| Buffer | 4 000 000 bytes úteis | PROP. | 4 000 mensagens, 40 s de geração sem escoamento |
| Overflow | descartar mensagem nova (drop-newest) | PROP. | Reprodutível; analisar consequências |
| Pacing FIFO | por definir no piloto | PILOTO | Medir backlog e capacidade antes de fixar; evitar sobrecarga artificial |
| Seed/run/streams | registar e emparelhar | OBR. | Repetições independentes |
| Deslocação do AP | -30 e +30 m (hipótese inicial) | PROP. | Selecionar dois casos críticos após piloto |

## Geometria temporal proposta

Posição do AP: (0,0,4 m); antena do autocarro: (x(t),0,2,5 m). Para velocidade `v` e paragem `s`:

```text
x(t) = v (t - 70)        se t < 70
x(t) = 0                se 70 <= t < 70+s
x(t) = v (t - 70 - s)   se t >= 70+s
```

O autocarro inicia a janela de geração em x(10)=-60v; assim, o início da paragem ocorre em t=70 s para todas as configurações, embora o trecho percorrido varie com v. **Não modela desaceleração/aceleração**, pelo que não se deve inferir efeitos dessas fases.

## Controlos para comparação justa

- Intervalo de geração `[10,130)`, sequência e ID iguais em ambas as políticas.
- Sem aplicações de fundo ou interferentes na baseline.
- Canal, taxa PHY, potência, alturas, antenas, controlo MAC, beacons e gestor de associação iguais em cada par.
- Mesma janela de medição; receções tardias observadas até t=200 s.
- Registar valores **efetivamente usados pelo ns-3**, não apenas os que o código pretendia configurar.
- Em `LogDistancePropagationLossModel`, definir explicitamente **ReferenceLoss por frequência**; o valor por omissão é de ~5,15 GHz.

## Configurações a congelar na M2

As linhas acima marcadas **PROP.** não devem aparecer no relatório como parâmetros empiricamente justificados antes da validação. Na M2, anotar: valor final, fonte, versão ns-3, comando que o aplicou e teste que o verificou.
