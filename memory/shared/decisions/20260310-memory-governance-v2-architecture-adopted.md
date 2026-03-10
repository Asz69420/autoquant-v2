---
id: "MEM-20260310-095559-8222"
bucket: "decisions"
title: "Memory Governance V2 Architecture Adopted"
actor: "oragorn"
source: "docs/MEMORY_GOVERNANCE_V2.md"
confidence: "high"
tags: ["memory-v2", "architecture", "governance"]
ts_iso: "2026-03-10T09:55:59.606477+00:00"
---

# Memory Governance V2 Architecture Adopted

## Summary
Adopted a shared-plus-private memory architecture with canonical rules, shared intelligence, private working memory, deterministic DB facts, and cold archive.

## Details
This establishes the governance spine for AutoQuant: task board, roadmap sync, completion records, and shared intelligence buckets. Facts remain in SQLite; durable lessons and fixes are promoted into shared memory; private journals remain bounded.

## Source
docs/MEMORY_GOVERNANCE_V2.md