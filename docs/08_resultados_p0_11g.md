# P0 — Resultado validado no WSL (IEEE 802.11g, ns-3.48)

**Data:** 23/11/2026. **Estado:** piloto P0 compilou e executou no WSL. Modelo de propagação verificado; cobertura e transporte UDP **não validados**.

## Reprodução e proveniência

Comando executado pelo grupo na raiz de `COMOV_NS3_B`:

```bash
bash scripts/run_p0.sh ../../ns-3
```

- Instalação utilizada: `/home/gb/COMOV/ns-3`, versão 3.48.
- Output original fornecido em conversa: `p0_11g.csv`.
- SHA-256 do CSV recebido: `5717bbfe69b644b69294cd485b26271601b042f8eac48145040f1d9b46f1ee3a`.
- Parâmetros: IEEE 802.11g, f=2,412 GHz, 20 dBm, OFDM 6 Mbit/s, n=3, d0=1 m, `ReferenceLoss=40,095329 dB`, alturas AP=4m/STA=2,5m.
- Separações horizontais analisadas: 0, 5, 10, 20, 50, 100, 200 m.

## Resultados observados

| Distância horizontal (m) | Distância 3D (m) | P_r teórica (dBm) | P_r modelo ns-3 (dBm) | Frames descodificados pela STA | RSS PHY (dBm) |
|---:|---:|---:|---:|---:|---:|
| 0 | 1,500 | -25,378067 | -25,378067 | 17 | -25,378067 |
| 5 | 5,220 | -41,625827 | -41,625827 | 17 | -41,625827 |
| 10 | 10,112 | -50,240279 | -50,240279 | 17 | -50,240279 |
| 20 | 20,056 | -59,162770 | -59,162770 | 17 | -59,162770 |
| 50 | 50,022 | -71,070290 | -71,070290 | 17 | -71,070290 |
| 100 | 100,011 | -80,096795 | -80,096795 | 17 | -80,096795 |
| 200 | 200,006 | -89,126596 | -89,126596 | 0 | não disponível |

### Conclusões estritamente suportadas

1. Foi testada com sucesso a integração do modelo `LogDistancePropagationLossModel` no canal do ns-3.48.
2. A verificação independente Python reportou **erro máximo de 0,000000 dB após arredondamento a 6 casas** contra a equação log-distance.
3. O RSS PHY registado nos frames descodificados coincidiu, à resolução do CSV, com a previsão do modelo.
4. Foram registados frames em seis das sete posições; a 200 m não foram observados frames descodificados pela STA durante a respetiva janela.

**Não concluir:** raio máximo de cobertura = 100 m, tempo útil de associação, PDR de UDP, margem do serviço, sensibilidade real ou desempenho num ambiente real. Os frames do P0 são frames Wi-Fi que chegaram ao receptor; não há aplicação UDP. A igualdade perfeita entre teoria e ns-3 é **esperada por construção** num modelo determinístico sem fading; é verificação de implementação, **não calibração experimental do canal**.

### Defeito identificado e corrigido no PR seguinte

No CSV original, a última linha (0 frames) tinha 11 campos, apesar de o cabeçalho definir 12: `phy_minus_model_db` estava ausente, em vez de explicitamente vazio. O `csv.DictReader` de Python representou esse último campo como `None`, sem bloquear a execução.

Correções na branch `fix/b10-p0-csv-validation`:

- `src/b10-p0-propagation.cc`: adicionar delimitador final para dois campos RSS vazios;
- `scripts/evaluate_p0.py`: rejeitar linhas com menos ou mais colunas.

**Consequência:** o CSV original, apesar de fornecer valores numéricos corretos, **não satisfaz a nova validação estrita do formato**. Depois de integrar o PR, repetir P0 para gerar um CSV estruturalmente correto.

### Próxima etapa

Piloto P1: implementar mobilidade contínua no eixo da estrada e gerar UDP 100 mensagens/s (1000 bytes, ID no instante de geração) durante a janela [10,130) s. Medir associações reais, receções e mensagens enviadas enquanto o veículo atravessa a região de cobertura, primeiro **sem buffer**. Variar velocidade e duração de paragem só depois de validar um único caso.
