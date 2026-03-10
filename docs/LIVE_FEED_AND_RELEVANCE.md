# Live Feed and Relevance Layer

## Purpose
Add richer external feed scaffolding and a deterministic relevance-scoring layer so external intel can be ranked before promotion.

## Added Components
- `config/live-feed-registry.json`
- `config/external-intel-relevance.json`
- `scripts/external_intel_relevance.py`
- `data/state/external_intel_relevance.json`

## What It Does
- defines future live feed slots for HyperLiquid and macro feeds
- scores normalized external-intel items for usefulness
- assigns dispositions:
  - shared_memory
  - handoff_only
  - archive_only
- runs during recurring maintenance

## Important Note
This is the ingestion/scoring scaffold. Actual live API fetching for disabled feeds still needs specific endpoint integration work.
