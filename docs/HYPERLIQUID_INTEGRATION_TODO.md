# HyperLiquid Integration TODO

## Status
Memory-system support for future HyperLiquid integration is already in place.

## Already Built
- source registry entry in `config/external-intel-sources.json`
- live-feed registry slots in `config/live-feed-registry.json`
- normalized external-intel storage in `data/external_intel/raw/` and `data/external_intel/normalized/`
- normalized item schema in `schemas/external-intel-item.schema.json`
- registry/bootstrap script in `scripts/external_intel_registry.py`
- relevance scoring in `config/external-intel-relevance.json` and `scripts/external_intel_relevance.py`
- retrieval path into:
  - `agents/quandalf/memory/briefing_packet.json`
  - `agents/quandalf/memory/cycle_orders.json`

## What Still Needs To Be Added Later
### 1. Concrete HyperLiquid fetchers
Add scripts for:
- liquidations feed fetch
- positioning / market-maker context fetch
- any funding/open-interest snapshot fetch not already covered elsewhere

Suggested location:
- `scripts/external_intel_hyperliquid.py`
- or split into:
  - `scripts/hyperliquid_liquidations.py`
  - `scripts/hyperliquid_positioning.py`

### 2. Endpoint mapping
Decide and document:
- exact HyperLiquid endpoints
- payload fields we care about
- polling cadence
- retry / timeout / rate-limit behavior

Suggested config location:
- `config/live-feed-registry.json`
- optional future file: `config/hyperliquid-feeds.json`

### 3. Normalization rules
Map returned payloads into `external-intel-item` records and/or deterministic state/DB inserts.

### 4. Promotion policy tuning
Decide what should:
- stay as deterministic facts only
- become shared regime notes
- become handoffs
- trigger strategy relevance scoring

## Where To Plug It In
- ingestion entrypoint: `scripts/external_intel_registry.py`
- scoring: `scripts/external_intel_relevance.py`
- recurring loop: `pipelines/daily-maintenance.lobster`
- retrieval consumers:
  - `scripts/research-cycle.py`
  - `scripts/build_cycle_orders.py`

## Recommendation
When ready, implement HyperLiquid as a deterministic feed adapter that writes normalized records first, then let the existing governance/scoring/retrieval system handle the rest.
