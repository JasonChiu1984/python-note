# Changelog

## v4.2.6 - 2026-05-22

- Re-reviewed the Python tutorial from a senior project-delivery perspective and confirmed the tutorial breadth/depth still meets the project-oriented learning target; the current highest-value gap was release-version drift inside specialized tutorial pages rather than missing new chapter coverage.
- Updated `python_cli_automation_engineering_tutorial.html`, `python_local_knowledge_base_mcp_tutorial.html`, and `python_project_delivery_blueprint_tutorial.html` so their visible version labels no longer lag behind the repository release state.
- Updated `VERSION` and the homepage release-state wording to `v4.2.6` so specialized tutorial pages and release evidence return to a single source of truth.
- Added a new dated review report, change list, and update record for the `v4.2.6` maintenance release.

## v4.2.5 - 2026-05-21

- Re-reviewed the Python tutorial from a senior project-delivery perspective and confirmed the tutorial breadth/depth still meets the project-oriented learning target; the current highest-value gap was release artifact path consistency after moving review/update records into per-day folders.
- Consolidated the release artifact archive structure under dated subdirectories for `審查報告/`, `內容需要更新的部分/`, and `更新資料/`, so the repository keeps long-running delivery records in a predictable timeline layout instead of a growing flat directory.
- Updated the remaining in-repo cross-references in `index.html`, `python_industrial_protocol_comparison_tutorial.html`, and `knowledge_base/entries/2026-05-16-124200-python-v330-data-evolution-update.md` to point at the dated artifact paths.
- Updated `VERSION` and the homepage release-state wording to `v4.2.5` so the repository records this pass as a release-artifact archive consistency maintenance release.
- Added a new dated review report, change list, and update record for the `v4.2.5` maintenance release.

## v4.2.4 - 2026-05-20

- Re-reviewed the Python tutorial from a senior project-delivery perspective and confirmed the tutorial breadth/depth still meets the project-oriented learning target; the real gap was release traceability drift left behind after the `v4.2.3` maintenance release.
- Updated the core release-tracked tutorial pages so their visible version labels now align with the repository release state instead of leaving `v4.2.2` markers in page titles, hero/status labels, and footer copy.
- Updated `VERSION` and the homepage release-state wording to `v4.2.4` so the repository records this pass as a focused page-version synchronization release.
- Added a new dated review report, change list, and update record for the `v4.2.4` maintenance release.

## v4.2.3 - 2026-05-19

- Re-reviewed the Python tutorial from a senior project-delivery perspective and confirmed the tutorial breadth/depth remains sufficient; the current highest-value gap is release hygiene recovery rather than a missing new chapter.
- Restored the canonical `CHANGELOG.md` after the workspace drifted into an accidental delete-plus-duplicate state (`CHANGELOG 2.md`), so the release history is again tracked at the expected path.
- Updated `VERSION` and the homepage release-state wording to `v4.2.3` so the repository clearly distinguishes this maintenance release from the earlier `v4.2.2` page-traceability update.
- Added a new dated review report, change list, and update record for the `v4.2.3` maintenance release.

## v4.2.2 - 2026-05-18

- Re-reviewed the Python tutorial from a senior project-delivery perspective and confirmed the remaining gap was release traceability consistency rather than another new topic.
- Corrected `index.html` so the homepage route summary now matches the actual 30 checked-in tutorial routes instead of the stale 28-route description.
- Added explicit version markers to `python_beginner_interactive_tutorial.html`, `python_interactive_tutorial.html`, and `python_intermediate_engineering_tutorial.html` so the foundational routes now expose release state directly in the page title, hero label, and footer.
- Updated `python_local_knowledge_base_mcp_tutorial.html` page-level version markers from `v4.0.0` to `v4.2.2` so the Local Knowledge Base MCP chapter reflects the post-maintenance release state.
- Added a new dated review report, change list, and update record for the v4.2.2 maintenance release.

## v4.2.1 - 2026-05-18

- Re-reviewed the Python tutorial from a senior project-delivery perspective and confirmed the remaining highest-value gap after v4.2.0 was release cleanliness in the local knowledge base rather than another new tutorial topic.
- Removed checked-in demo/export validation entries from `knowledge_base/index.json` and `knowledge_base/entries/` so the published repository keeps only durable project knowledge instead of mixed demonstration artifacts.
- Clarified `knowledge_base/README.md` best-practice guidance so temporary demo or smoke data is treated as non-release content.
- Added a new dated review report, change list, and update record for the v4.2.1 maintenance release.

## v4.2.0 - 2026-05-18

- Re-reviewed the full Python tutorial from a senior project-development perspective after v4.1.0 and confirmed the highest-value local-verifiable gap was no longer another isolated framework topic, but the missing integrated project-delivery blueprint that ties existing chapters into one shippable reference flow.
- Added `python_project_delivery_blueprint_tutorial.html` with 24 lesson cards covering architecture boundary, config contract, idempotency, fail-safe alarm handling, release evidence, runbook, verification, and handoff strategy.
- Added `範例程式碼/project_delivery_blueprint/` as a zero-dependency standard-library reference project with `config` / `domain` / `service` split, duplicate filtering, alarm handling, outbox evidence, unittest coverage, and a smoke script.
- Updated `index.html` to expose the new Project Delivery Blueprint route and show the updated v4.2.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v4.1.0 - 2026-05-18

- Re-reviewed the full Python tutorial from a senior project-development perspective after v4.0.0 and confirmed the highest-value local-verifiable gap was standalone CLI automation engineering rather than another framework or protocol topic.
- Added `python_cli_automation_engineering_tutorial.html` with 24 interactive lesson cards covering command contract, `plan / apply / report`, `--dry-run`, exit code policy, JSON evidence, and operator handoff.
- Added `範例程式碼/cli_automation_engineering/` as a zero-dependency standard-library sample with manifest validation, structured execution reports, subcommand CLI, unittest coverage, and smoke verification.
- Updated `index.html` to expose the new CLI automation engineering route and show the updated v4.1.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.

## v4.0.0 - 2026-05-17

- Re-reviewed the full Python tutorial from a senior project-development perspective against the actual workspace state and confirmed the highest-value local-verifiable gap was not another generic engineering topic, but the missing teaching route for the already-implemented local knowledge base and MCP workflow.
- Added `python_local_knowledge_base_mcp_tutorial.html` with 24 interactive lesson cards covering conversation export, dual-format storage, index contract, stable entry id, MCP `initialize` / `tools/list` / `tools/call`, search/read verification, troubleshooting, and release evidence.
- Kept the tutorial aligned with the real repository implementation in `knowledge_base/`, `scripts/export_conversation.py`, and `mcp_server/knowledge_base_server.py` instead of introducing a disconnected sample.
- Updated `index.html` to expose the new local knowledge base MCP route and show the updated v4.0.0 status.
- Added review-driven delivery artifacts under `審查報告`, `內容需要更新的部分`, and `更新資料`.
