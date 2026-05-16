# Changelog

## v3.3.0 - 2026-05-16

- Re-reviewed the full Python tutorial from a senior project-development perspective after v3.2.0 added the configuration governance route.
- Confirmed the next highest-value project-depth gap was a standalone data evolution governance route covering schema version, compat read/write, expand/contract, backfill checkpoint, drift preflight, rollback validation, and release evidence.
- Added `python_data_evolution_governance_tutorial.html` with 32 interactive lesson cards covering overview, architecture, setup, configuration, example, verification, troubleshooting, and best practices.
- Added `範例程式碼/data_evolution_governance/` as a zero-dependency standard-library sample with schema manifest, compat reader, backfill checkpoint, preflight drift checks, rollback validation, unittest coverage, and a smoke script.
- Updated `index.html` to show twenty-three tutorial routes, data evolution governance progress, a new route card, and the updated v3.3.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v3.2.0 - 2026-05-14

- Re-reviewed the full Python tutorial from a senior project-development perspective after v3.1.0 added the event-driven reliability route.
- Confirmed the next highest-value project-depth gap was a standalone configuration governance route covering env precedence, secret boundary, typed settings, feature flags, validation, redacted config evidence, and multi-environment handoff.
- Added `python_configuration_governance_tutorial.html` with 32 interactive lesson cards covering overview, architecture, setup, configuration, example, verification, troubleshooting, and best practices.
- Added `範例程式碼/configuration_governance/` as a zero-dependency standard-library sample with configuration loader, precedence rules, secret-file override, CLI override, config validation, redacted report output, unittest coverage, and a smoke script.
- Updated `index.html` to show twenty-two tutorial routes, configuration governance progress, a new route card, and the updated v3.2.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v3.1.0 - 2026-05-14

- Re-reviewed the full Python tutorial from a senior project-development perspective after v3.0.0 added the performance and memory engineering route.
- Confirmed the next highest-value project-depth gap was a standalone event-driven reliability route covering transactional outbox, idempotent consumer, dead-letter queue, replay, ordering boundary, operator runbook, and release evidence.
- Added `python_event_driven_reliability_tutorial.html` with 32 interactive lesson cards covering overview, architecture, setup, configuration, example, verification, troubleshooting, and best practices.
- Added `範例程式碼/event_reliability/` as a zero-dependency standard-library sample with in-memory outbox, fake broker, idempotent consumer, DLQ handling, replay flow, unittest coverage, and a smoke script.
- Updated `index.html` to show twenty-one tutorial routes, event reliability progress, a new route card, and the updated v3.1.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v3.0.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.9.0 added the API integration resilience route.
- Confirmed the next highest-value project-depth gap was a standalone performance and memory engineering route covering benchmark baseline, `cProfile`, `pstats`, `tracemalloc`, latency budget, memory budget, regression gate, and release evidence.
- Added `python_performance_memory_engineering_tutorial.html` with 32 interactive lesson cards covering overview, architecture, setup, configuration, example, verification, troubleshooting, and best practices.
- Added `範例程式碼/performance_memory_engineering/` as a zero-dependency standard-library sample with reproducible workload generation, slow/optimized aggregation paths, benchmark measurement, profile report, memory snapshot, budget decision, unittest coverage, and a smoke script.
- Updated `index.html` to show twenty tutorial routes, performance/memory progress, a new route-map node, and the updated v3.0.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.9.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.8.0 added the type contract engineering route.
- Confirmed the next highest-value project-depth gap was a standalone API integration resilience route covering timeout budget, retry policy, idempotency, rate limiting, circuit breaker, response schema validation, metrics, degraded behavior, and integration evidence.
- Added `python_integration_resilience_tutorial.html` with 32 interactive lesson cards covering overview, architecture, setup, configuration, example, verification, troubleshooting, and best practices.
- Added `範例程式碼/integration_resilience/` as a zero-dependency standard-library sample with `HttpTransport` Protocol, fake transport, retry policy, fixed-window rate limiter, circuit breaker, idempotency enforcement, response schema validation, unittest coverage, and a smoke script.
- Updated `index.html` to show nineteen tutorial routes, API integration resilience progress, a new route-map node, and the updated v2.9.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.8.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.7.0 added the CI/CD quality gate route.
- Confirmed the next highest-value project-depth gap was a standalone type contract engineering route covering type hints, `TypedDict`, `dataclass`, `Protocol`, runtime validation, schema boundary, static-analysis policy, alarm handling, fail-safe behavior, and contract evidence.
- Added `python_type_contract_engineering_tutorial.html` with 32 interactive lesson cards covering overview, architecture, setup, configuration, example, verification, troubleshooting, and best practices.
- Added `範例程式碼/type_contract_engineering/` as a zero-dependency standard-library sample with payload validation, domain dataclass invariants, Protocol-based alarm publisher, fail-safe evaluation, contract report output, unittest coverage, and a smoke script.
- Updated `index.html` to show eighteen tutorial routes, type contract progress, a new route-map node, and the updated v2.8.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.7.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.6.0 added the deployment runtime route.
- Confirmed the next highest-value project-depth gap was a standalone CI/CD quality gate route covering workflow triggers, local gate commands, runtime matrix, coverage policy, blocking/non-blocking checks, artifact evidence, release decision, and rollback notes.
- Added `python_ci_quality_gate_tutorial.html` with 28 interactive lesson cards covering gate contract, `py_compile`, `unittest`, smoke entrypoint, fail-fast behavior, Python 3.14 stable lane, Python 3.15 beta preview lane, coverage policy, GitHub Actions workflow, artifact traceability, and industrial deployment evidence.
- Added `範例程式碼/ci_quality_gate/` as a zero-dependency standard-library sample with compile gate, unittest gate, simplified coverage policy, runtime matrix policy, workflow contract validation, fail-fast pipeline behavior, evidence manifest output, and a GitHub Actions workflow template.
- Updated `index.html` to show seventeen tutorial routes, CI/CD quality gate progress, a new route-map node, and the updated v2.7.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.6.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.5.0 added the industrial data gateway route.
- Confirmed the next highest-value project-depth gap was a standalone deployment runtime route covering Dockerfile, Compose, environment configuration, health/readiness, structured logging, signal handling, resource limits, restart policy, image tag/digest, deployment smoke, and rollback evidence.
- Added `python_deployment_runtime_tutorial.html` with 28 interactive lesson cards covering runtime contract, Docker build boundary, `.dockerignore`, non-root user, env config validation, secret redaction, `/healthz`, `/readyz`, dependency degraded state, draining, graceful shutdown, resource limits, network exposure, deployment evidence, and rollback limits.
- Added `範例程式碼/deployment_runtime_service/` as a zero-dependency standard-library sample with runtime config loading, HTTP health/readiness contracts, structured JSON logging, signal-aware shutdown state, Dockerfile/Compose/static deployment contract validation, unittest coverage, and a smoke script.
- Updated `index.html` to show sixteen tutorial routes, deployment runtime progress, a new route-map node, and the updated v2.6.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.5.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.4.0 added the packaging and release engineering route.
- Confirmed the next highest-value project-depth gap was an industrial data gateway route aligned with PLC/DDC/SCADA, Modbus, OPC UA, BACnet, MQTT, alarm handling, fail-safe behavior, and site deployment.
- Added `python_industrial_data_gateway_tutorial.html` with 32 interactive lesson cards covering gateway architecture, IO mapping, Modbus FC03/FC16 and float conversion, OPC UA endpoint and NodeId, BACnet object/routing, MQTT payloads, timeout, retry, stale data, alarm handling, fail-safe, VLAN, firewall, handover evidence, and sample-project operation.
- Added `範例程式碼/industrial_data_gateway/` as a zero-dependency standard-library sample with Modbus holding-register simulation, 16-bit to 32-bit float conversion, polling, alarm evaluation, fail-safe output, OPC UA/BACnet/MQTT contract report, unittest coverage, and a smoke script.
- Updated `index.html` to show fifteen tutorial routes, industrial gateway progress, a new route-map node, and the updated v2.5.0 status while preserving the existing SVG connector color/layout corrections.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.4.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.3.0 added the async concurrency engineering route.
- Confirmed the next highest-value project-depth gap was a standalone packaging and release engineering route rather than another syntax, testing, security, or async expansion route.
- Added `python_packaging_release_engineering_tutorial.html` with 28 interactive lesson cards covering `pyproject.toml`, src layout, entry points, semantic versioning, changelog gate, deterministic source archives, checksums, release manifest, CI gates, rollback, token scope, and audit evidence.
- Added `範例程式碼/packaging_release_engineering/` as a zero-dependency standard-library sample with metadata validation, package version checks, changelog verification, deterministic source archive creation, SHA-256 checksum generation, release manifest writing, unittest coverage, and a smoke script.
- Updated `index.html` to show fourteen tutorial routes, packaging release progress, a new route-map node, and the updated v2.4.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.3.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.2.0 added the security engineering route.
- Confirmed the next highest-value project-depth gap was a standalone async concurrency engineering route rather than another security, testing, or syntax expansion route.
- Added `python_async_concurrency_engineering_tutorial.html` with 28 interactive lesson cards covering event loop, coroutine/task ownership, TaskGroup, bounded queue, backpressure, timeout, retry, cancellation, async testing, worker metrics, and release smoke evidence.
- Added `範例程式碼/async_concurrency_engineering/` as a zero-dependency standard-library sample with `asyncio.Queue`, bounded workers, per-item timeout, retryable error handling, cancellation-safe shutdown, `unittest.IsolatedAsyncioTestCase`, and a smoke script.
- Updated `index.html` to show thirteen tutorial routes, async concurrency progress, a new route-map node, and the updated v2.3.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.2.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.1.0 added the observability and operations route.
- Confirmed the next highest-value project-depth gap was a standalone security engineering route rather than another syntax or case-expansion route.
- Added `python_security_engineering_tutorial.html` with 28 interactive lesson cards covering threat modeling, authentication, authorization, input validation, secret handling, supply-chain evidence, runtime controls, audit logs, and security incident evidence.
- Added `範例程式碼/security_engineering/` as a zero-dependency standard-library sample with PBKDF2 password hashing, constant-time token comparison, deny-by-default RBAC policy, validation, rate limiting, redacted audit logs, manifest gate, unittest coverage, and a smoke script.
- Updated `index.html` to show twelve tutorial routes, security engineering progress, a new route-map node, and the updated v2.2.0 status while preserving the latest route-map layout corrections.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.1.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v2.0.0 added the testing engineering route.
- Confirmed the next highest-value project-depth gap was production observability and operations rather than another syntax or case-expansion route.
- Added `python_observability_operations_tutorial.html` with 28 interactive lesson cards covering structured logging, metrics, tracing, health checks, SLO, alert triage, runbooks, rollback evidence, and incident records.
- Added `範例程式碼/observability_operations/` as a zero-dependency standard-library sample with telemetry collector, observed service, health report, SLO evaluation, unittest coverage, and a smoke script.
- Updated `index.html` to show eleven tutorial routes, observability operations progress, a new route-map node, and the updated v2.1.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v2.0.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective after v1.9.0 completed the high-level 100-case semantic review.
- Confirmed the next highest-value project-depth gap was a standalone testing engineering route rather than more advanced-case expansion.
- Added `python_testing_engineering_tutorial.html` with 30 interactive lesson cards covering testing strategy, fixtures, unit tests, integration tests, quality signals, CI gates, and release evidence.
- Added `範例程式碼/testing_quality_gate/` as a zero-dependency standard-library sample with domain rules, fake repository, `unittest` coverage, demo smoke, and a `py_compile + unittest` quality gate script.
- Updated `index.html` to show ten tutorial routes, testing engineering progress, the testing route map node, and the updated v2.0.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v1.9.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective.
- Confirmed the broad route set remains sufficient; the highest-value local gap was the final 10 high-level advanced cases still marked as pending semantic deepening.
- Added v1.9.0 case-specific focus, failure path, and implementation notes for Backward Compatible DTO, Data Dedup Pipeline, Priority Queue, Reconciliation Job, Compression Tradeoff, Path Traversal Guard, Fuzzing Parser, WebSocket Heartbeat, Streaming Response, and Vector Search Refresh.
- Advanced the high-level 100-case review state from 90/100 to 100/100.
- Updated `index.html`, `python_advanced_engineering_cases.html`, and `VERSION` to show v1.9.0 and the 100/100 reviewed state.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v1.8.0 - 2026-05-13

- Re-reviewed the full Python tutorial from a senior project-development perspective.
- Confirmed the broad route set remains sufficient; the highest-value local gap is still high-level advanced-case semantic maturity.
- Added v1.8.0 case-specific focus, failure path, and implementation notes for API Versioning, Atomic File Write, Delayed Job Scheduler, Search Index Sync, Large JSON Encoding, Input Size Limit, Mutation Testing, ASGI Background Task, Docker Layer Cache, and ML Batch Inference.
- Advanced the high-level 100-case review state from 80/100 to 90/100.
- Updated `index.html` and `python_advanced_engineering_cases.html` to show v1.8.0 and the 90/100 reviewed state.

## v1.7.0 - 2026-05-13

- Corrected the v1.6.0 semantic metadata mismatch for case 61 from Saga Compensation to Distributed Lock.
- Added the seventh advanced semantic review batch in `python_advanced_engineering_cases.html`.
- Advanced the high-level 100-case review state from 70/100 to 80/100.
- Added v1.7.0 case-specific focus, failure path, and implementation notes for Saga Compensation, Streaming Upload, Job Lease, Leader Election, Gunicorn Worker Tuning, PII Masking, Property-Based Test, Feature Toggle Debt, Reproducible Build, and Image Processing Pipeline.
- Updated `index.html` to show v1.7.0 and the 80/100 reviewed state.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v1.6.0 - 2026-05-13

- Added the sixth advanced semantic review batch in `python_advanced_engineering_cases.html`.
- Advanced the high-level 100-case review state from 60/100 to 70/100.
- Added v1.6.0 case-specific focus, failure path, and implementation notes for State Machine, Bulk Import Validation, Graceful Shutdown, Distributed Lock, Backfill Job, Audit Log, Golden Master Test, Runbook Automation, Dependency Vulnerability Gate, and Safe Deserialization.
- Updated `index.html` to show v1.6.0 and the 70/100 reviewed state.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v1.5.0 - 2026-05-13

- Added the fifth advanced semantic review batch in `python_advanced_engineering_cases.html`.
- Advanced the high-level 100-case review state from 50/100 to 60/100.
- Added v1.5.0 case-specific focus, failure path, and implementation notes for Event Sourcing Snapshot, API Pagination, Request Coalescing, Exactly Once Illusion, Adaptive Batch Size, RBAC Permission Check, Contract Test, Alert Dedup, Subprocess Timeout, and Encryption at Rest.
- Updated `index.html` to show v1.5.0 and the 60/100 reviewed state.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.
