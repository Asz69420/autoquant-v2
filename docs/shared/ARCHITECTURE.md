# AutoQuant Architecture
## Pipeline Flow
ResearchCard → Thesis → StrategySpec → BacktestResult → Lesson/Promotion → Refinement
## Agents
- Oragorn: Commander (chat, triggers Lobster pipelines)
- Quandalf: Strategist (llm-task reasoning)
- Frodex: Execution (code, data, files)
- Balrog: Firewall (deterministic validation)
- Smaug: Live trader (future, terminal-isolated)
## Data Layer
- JSON schemas: pipeline interchange
- SQLite: persistent queryable store
- Structured memory folders: per-agent context
- NDJSON event logs: audit trail
## Principles
1. Pipeline owns orchestration
2. Lobster for recurring workflows
3.Approval gates on all side effects
4. Schema-validated LLM steps via llm-task
5. Evidence-based completion
6. Right model for the right step
