# Delegation Reliability

## Current Reality
AutoQuant's direct execution path is currently more reliable than delegation/background completion handoff.

## Policy
- direct execution is the default
- background/delegation is for long compute only
- every delegated run must be verified by output, file creation, state change, or completion artifact
- if delegation handoff fails, finish the work directly

## Why
This prevents invisible stalls, false confidence, and the feeling that work only finishes after manual pushing.

## Immediate Implication
Oragorn should behave as a hands-on commander first and a delegator second until delegation reliability improves.
