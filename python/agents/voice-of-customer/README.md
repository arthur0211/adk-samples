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

## Testes

Execute os testes unitários com:

```bash
cd python/agents/voice-of-customer
pytest
```

Os testes cobrem os fluxos críticos do `PlanManager`, garantindo que o estado do
supervisor reflita corretamente a lista de tarefas do planner.
