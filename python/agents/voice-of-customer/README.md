# Avenue Deep Dive Voice of Customer Agent

Este projeto demonstra como construir um sistema multi-agente para análises de
Voz do Cliente (VoC) seguindo o padrão utilizado pelo time do Google nas demos
do Agent Development Kit (ADK). O agente supervisor orquestra uma cadeia com
subagentes especializados em planejamento, coleta de dados, análises
quantitativas e qualitativas, além de um agente reporter responsável pela
síntese final.

## Componentes Principais

- **Supervisor Agent**: Interface com o usuário. Garante o cumprimento do
  protocolo operacional, aciona o planner antes de qualquer análise e mantém um
  to-do list persistido no estado usando ferramentas de gerenciamento de plano.
- **Planner/Clarifier Agent**: Traduz a solicitação do usuário em um plano
  estruturado no formato definido pela Avenue Deep Dive. Produz tarefas com
  ordem de execução, agente responsável e flag de conclusão.
- **Data Collector Agent**: Reúne bases anonimizadas de VoC necessárias para as
  análises seguintes.
- **Quantitative Analyst Agent**: Calcula métricas, KPIs e sumariza tendências
  numéricas.
- **Qualitative Analyst Agent**: Destila sentimentos, temas e insights
  qualitativos.
- **Reporter Agent**: Gera o relatório final consolidado.

## Gerenciamento do Plano

O arquivo [`shared/plan.py`](voice_of_customer/shared/plan.py) contém a classe
`PlanManager`, responsável por:

1. Interpretar o output JSON do planner (mesmo quando combinado com texto
   livre), convertendo-o em uma estrutura tipada.
2. Persistir o plano no estado da sessão (`session.state`), incluindo uma cópia
   bruta para auditoria.
3. Marcar tarefas como concluídas, recalculando automaticamente o status de cada
   etapa.
4. Gerar resumos e representações em Markdown do progresso atual.

As funções expostas em [`tools/plan_management.py`](voice_of_customer/tools/plan_management.py)
fornecem **FunctionTools** que o supervisor pode chamar durante a execução para
registrar o plano, atualizar tarefas, consultar o status ou resetar o workflow.
Cada função responde com metadados estruturados (como `has_plan`) e códigos de
erro descritivos (`plan_parsing_error`, `plan_not_found`, `task_not_found`),
garantindo que o supervisor consiga reagir rapidamente a inconsistências do
planner ou a ordens de execução inválidas.

Para cumprir o protocolo de transparência da Avenue, toda vez que o supervisor
apresentar o resultado de `store_supervisor_plan`, `mark_supervisor_task_completed`,
`get_supervisor_plan_status` ou `reset_supervisor_plan` ao usuário, ele deve
preservar a mensagem literal retornada pelo tool usando o formato
`[NomeDaFerramenta] tool reported: ...`. O helper
`format_plan_tool_status(tool_name, response)` centraliza essa formatação e
gera textos como:

```
store_supervisor_plan tool reported: Plano registrado no estado do supervisor. Total de tarefas registradas: 5. Pendentes: 5. Etapas no plano: 2.
```

Ao utilizar essa string diretamente na conversa, o usuário tem visibilidade
completa do que cada ferramenta reportou.


## Contrato de Estado Compartilhado

O módulo [`shared/state.py`](voice_of_customer/shared/state.py) centraliza o
estado compartilhado utilizado pelos subagentes. Ele inicializa a sessão com
uma estrutura padrão contendo:

- `plan_metadata`: metadados sobre o pedido em andamento (resumo, período,
  audiência alvo).
- `collected_datasets`: lista de datasets agregados e anonimizados coletados
  pelo `data_collector_agent`.
- `quantitative_insights`: resumo e métricas estruturadas geradas pelo
  `quanti_analyst_agent`.
- `qualitative_insights`: resumo, temas e citações representativas compiladas
  pelo `quali_analyst_agent`.
- `reporter_handoff`: informações finais para o `reporter_agent`, incluindo o
  status do hand-off, entregáveis e próximos passos.

O `root_agent` registra o callback `load_default_state` como
`before_agent_callback`, garantindo que a estrutura seja carregada antes da
primeira interação e permitindo carregar fixtures (via variável de ambiente
`VOICE_OF_CUSTOMER_SCENARIO`) para demos ou testes.

Para simplificar a persistência de resultados, expomos ferramentas em
[`tools/shared_state.py`](voice_of_customer/tools/shared_state.py):

- `record_plan_metadata`
- `record_dataset`
- `record_quanti_summary`
- `record_quali_summary`
- `record_reporter_handoff`
- `get_reporter_snapshot`

Essas funções padronizam a gravação no `ToolContext.state` e retornam metadados
úteis (quantidade de datasets, contagem de métricas, status do hand-off etc.),
facilitando a coordenação entre os subagentes.


## Testes

Execute os testes unitários com:

```bash
cd python/agents/voice-of-customer
pytest
```

Os testes cobrem os fluxos críticos do `PlanManager` e das ferramentas de plano
do supervisor, garantindo que o estado reflita corretamente a lista de tarefas,
que o markdown esteja alinhado ao progresso real e que erros de parsing ou
ordens inválidas sejam reportados de forma previsível.
