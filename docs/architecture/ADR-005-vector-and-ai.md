# ADR-005: Keep recommendations deterministic; defer vector and ML services

## Context

The current product detects explicit telemetry conditions and applies explainable financial formulas. There is no curated recommendation corpus or validated model training dataset that requires semantic retrieval or predictive inference.

## Decision

Use deterministic rules and store their resulting recommendations in PostgreSQL. Do not install pgvector, a separate vector database, or an AI/ML service in the demo architecture.

## Alternatives

- Add pgvector embeddings for an operational recommendation library.
- Add an ML model to predict future maintenance or driver risk.
- Keep calculations and rules deterministic.

## Consequences

Financial estimates and rule triggers remain testable and explainable. Semantic retrieval and prediction are deferred until there is a vetted playbook or representative, permissioned training data and a clear evaluation plan.
