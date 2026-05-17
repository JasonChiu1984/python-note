# Architecture Decisions

## ADR-001: Separate domain from adapters

- context: Industrial gateway and general service logic need stable domain rules without leaking protocol details.
- decision: `domain` does not import `adapters`; `application` orchestrates both.
- tradeoff: More files and explicit translation layers, but lower coupling.
- replacement_trigger: If the project becomes a plugin platform, introduce a dedicated interface layer instead of direct adapter references.

## ADR-002: Deprecate legacy gateway facade

- context: `legacy_gateway.run()` hides timeout, alarm, and retry semantics.
- decision: Move callers to `gateway_service.start()` with explicit configuration and health reporting.
- tradeoff: Short-term migration cost for clearer runtime behavior.
- replacement_trigger: Remove the legacy facade after the sunset date once all callers migrate.
