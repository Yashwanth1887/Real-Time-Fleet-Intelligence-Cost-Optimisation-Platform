# ADR-004: Deterministic rule and cost engine

## Context

Managers need a clear explanation of what happened and how each currency estimate was produced.

## Decision

Use rule-based thresholds and Decimal arithmetic for cost/savings estimates. Store the formula, rate, duration, and resulting amount with each cost event.

## Alternatives

- Use an opaque predictive model to produce costs.
- Display telemetry without financial interpretation.
- Use binary floating point and omit formula details.

## Consequences

Results can be tested and traced to explicit assumptions. Estimates depend on configured fuel price and reported fuel rate and must not be mistaken for actual invoices.
