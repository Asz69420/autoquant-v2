# AutoQuant Agent Framework vNext

## Goal
Provide one shared framework for all agents while preserving role-specific specialization.

## Shared Skeleton For All Agents
Every agent should have:
1. an operating file
2. a bounded work loop
3. structured work objects
4. layered memory
5. explicit decision outcomes
6. strong retrieval discipline
7. audit/archive separation

## Shared Components

### 1. Operating File
The live file that tells the agent what it is currently optimizing for.
Examples:
- research priorities
- banned failure patterns
- rotation policy
- current interventions
- what counts as success

### 2. Structured Work Objects
Every agent should work through compact objects rather than vague prose where possible.
Examples:
- Quandalf: experiment objects
- Logron: incident objects
- Frodex: fix/run objects
- Oragorn: intervention / orchestration decision objects
- Analyser: verdict objects

### 3. Layered Memory
Use the memory system documented in `MEMORY_SYSTEM_VNEXT.md`.

### 4. Explicit Outcomes
No limbo states.
Every meaningful unit of work ends in an explicit outcome.
Examples depend on agent role.

### 5. Retrieval Discipline
Default to active + distilled memory.
Archive only when needed.

## Agent Specialization

### Oragorn
Role:
- commander
- orchestration
- intervention logic

Needs:
- system priorities
- current bottlenecks
- cross-agent awareness
- decision history

### Quandalf
Role:
- strategy research brain

Needs:
- research program
- experiment memory
- distilled lessons
- lane authority and validation basket awareness

### Logron
Role:
- watcher / health / anomaly detection

Needs:
- incident memory
- threshold history
- recurring failure patterns
- escalation rules

### Frodex / main execution agent
Role:
- execution, data, code, tooling

Needs:
- known fixes
- tool workflows
- execution failures
- reliable procedure memory

### Analyser / verdict agents
Role:
- evaluation, doctrine, calibration

Needs:
- verdict history
- calibration memory
- doctrine updates
- family and regime comparison priors

## Why Not Make All Agents Identical
Because role truth-filters differ.
Research, monitoring, execution, and evaluation are not the same task.
The skeleton should be shared.
The organs should differ.

## Implementation Rule
Shared framework:
- same architecture
- same memory logic
- same anti-bloat rules
- same documentation shape

Agent-specific adaptation:
- different operating files
- different work objects
- different outcome vocabulary
- different promotion thresholds

## Current Direction
The Quandalf/Oragorn path is the most advanced implementation of this framework.
That path should act as the reference implementation for extending the pattern to the other agents.

## Core Principle
Shared skeleton. Specialized organs.
