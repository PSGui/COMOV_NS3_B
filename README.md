# COMOV_NS3_B — Projeto B10

**COMOV 2026/27: Bus Data Transfer at a Stop**

Estudo no ns-3 de transferência UDP entre um autocarro móvel e um AP Wi-Fi durante uma paragem, comparando **envio imediato** com **armazenamento FIFO de aplicação**.

> **Estado atual:** planeamento e cálculos teóricos. **O código P0 para ns-3.48 já existe, mas ainda não foi compilado/executado no WSL nem existem resultados experimentais confirmados.** Os parâmetros não impostos no enunciado são provisórios até M2.

## Navegação

- [Objetivo, hipóteses e decisões](docs/01_escopo_e_decisoes.md)
- [Tabela rastreável de parâmetros](docs/02_parametros.md)
- [Modelo teórico e todas as contas principais](docs/03_modelo_teorico.md)
- [12 simulações obrigatórias, pilotos e robustez](docs/04_matriz_simulacoes.md)
- [Validação independente dos CSV do preflight](docs/05_validacao_preflight.md)
- [P0 — propagação no ns-3.48 e execução no WSL](docs/07_p0_ns3_48.md)
- [Referências e documentação ns-3](docs/06_referencias.md)
- [Configuração legível por máquina](params/reference.json)
- [Calculadora independente e geração de matriz CSV](scripts/preflight.py)

## Primeiros comandos (WSL)

```bash
git clone https://github.com/PSGui/COMOV_NS3_B.git
cd COMOV_NS3_B
python3 scripts/preflight.py
```

A calculadora usa apenas a biblioteca padrão Python. Produz `out/preflight/matrix.csv` (12 linhas) e `out/preflight/theory.csv`; **são resultados analíticos, não simulações**. Os ficheiros `out/` são descartáveis e não se devem confundir com os dados brutos das simulações.

## Regras de qualidade

1. Parametrizar tudo, nunca alterar manualmente os resultados em relatórios.
2. Justificar escolhas e guardar versão exata de ns-3, seed/run/streams.
3. Dar ID a todas as mensagens **na geração** e distinguir receção no prazo, tardia, drop e pendente.
4. Calcular a teoria **antes** de ver os resultados e guardar diferenças.
5. Uma execução = uma observação; diferenças emparelhadas e IC95%.
6. Nunca declarar validada uma simulação sem os logs e teste de reprodução.

## Fluxo Git

Criar branch por mudança, descrever pressupostos e validar alterações antes de integrar em `main`. No WSL usar `git pull` depois de integrar o pull request.

## Próximo desenvolvimento

Executar o código de P0 em `src/b10-p0-propagation.cc` com `bash scripts/run_p0.sh /caminho/para/ns-3.48` (ver guia P0). Após validação: implementar `src/b10-bus-stop.cc`, instrumentar UDP, mobilidade, associação e só depois FIFO.

## Enunciado

A ficha B10 exige as 12 combinações de velocidade, paragem e política, comparação do volume entregue e da entrega em 60 s, IC95%, acompanhamento do buffer e da associação, contabilidade e robustez deslocando AP. Relatório até 10 páginas (+ referências) e pacote reproduzível.

## Piloto P0 com ns-3.48

```bash
# No diretório COMOV_NS3_B, depois do merge da branch:
git pull
bash scripts/run_p0.sh /caminho/para/ns-3.48
```

O caminho tem de apontar para a instalação real do simulador. O script cria `out/p0/p0_11g.csv` e verifica independentemente as diferenças teóricas; compilação ainda não testada nesta fase.
