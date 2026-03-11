# AutoQuant Memory System vNext

## Purpose
This document explains the memory architecture now used across AutoQuant, why it exists, and how to debug or extend it later.

## Design Goal
Preserve learning without bloating context.

The system needs:
- fast local working context
- structured experiment memory
- distilled durable lessons
- full audit/archive history

A flat notebook is too weak.
A giant archive loaded every turn is too noisy.
So the system uses layered memory with strict promotion rules.

## The Layers

### Layer 0 — Active Scratchpad
Fast, local, disposable working context.
Used for:
- current hypotheses
- immediate comparisons
- active lane choices
- short-lived cycle notes

Rules:
- write freely
- read by default during active work
- do not treat as truth
- do not let it directly steer high-stakes decisions without promotion

### Layer 1 — Experiment Memory
Structured records of what was actually tested.
Used for:
- hypothesis
- lane
- mutation surface
- expected effect
- actual effect
- diagnosis
- decision
- lesson extracted

Rules:
- one experiment object per strategy test
- should be compact and queryable
- this is the main learning substrate for iterative work

### Layer 2 — Distilled Lessons
Promoted, evidence-backed lessons.
Used for:
- repeated failure patterns
- stable mechanism insights
- durable lane/regime guidance
- family-level priors

Rules:
- promotion requires evidence, not vibes
- dedupe repeated lessons
- include confidence / review / expiry metadata where possible
- this is the default durable retrieval layer

### Layer 3 — Archive / Audit
Raw journals, old artifacts, historical run outputs, and complete traces.
Used for:
- recovery
- debugging
- audits
- deep retrospective analysis

Rules:
- write-heavy, read-light
- not default context
- compress and archive aggressively

## Why This Works
- keeps active context small
- preserves real learning
- separates observations from promoted knowledge
- prevents old noise from dominating live reasoning
- makes debugging possible because raw history still exists

## Retrieval Policy
Default retrieval should prefer:
1. active scratchpad
2. recent experiment memory
3. distilled lessons
4. archive only on demand

Archive is not default context.
That is intentional.

## Promotion Rules
### Scratchpad -> Experiment Memory
Promote when an actual test or decision happened.

### Experiment Memory -> Distilled Lessons
Promote when:
- evidence repeats
- diagnosis is stable
- lesson is reusable
- it changes future behavior

### Distilled Lessons -> Strong Priors
Promote only when the pattern has survived validation and still makes sense across time/regime variation.

## Anti-Bloat Rules
- do not append endlessly when merging would do
- compress repeated failures into one canonical lesson
- expire stale lessons
- archive old experiment detail instead of loading it by default
- keep journals separate from system-of-record memory

## Agent Adaptation
All agents should use the same skeleton:
- active context
- structured work memory
- distilled lessons
- archive

But each agent adapts the content:
- Quandalf: strategy experiments and diagnosis
- Logron: incidents, thresholds, recurring operational failures
- Frodex/main: fixes, tool workflows, execution failures, known-good procedures
- Oragorn: orchestration decisions, intervention logic, system-level priorities
- Analyser/quandalf-lite: verdict history, doctrine, calibration, compact experimental priors

## Current AutoQuant Implementation
Currently live in Oragorn/Quandalf path:
- `research_program.json` = operating file / search priorities
- `latest_experiment_memory.json` = structured experiment layer
- `latest_learning_loop.json` = distilled durable learning layer
- journals + artifacts + logs = archive/audit layer

## Debug Checklist
If memory feels bad, check in this order:
1. Is active context too large?
2. Are experiment objects missing or malformed?
3. Are lessons being promoted without enough evidence?
4. Is archive leaking into default retrieval?
5. Are stale lessons not being expired/reviewed?
6. Is the agent reading the right layer for the job?

## Core Principle
Simple capture. Structured retention. Selective retrieval.
