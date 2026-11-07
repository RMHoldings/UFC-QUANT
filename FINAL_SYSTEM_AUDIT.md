# UFCQuant — Full System Functional Audit (Phase 20 archive)

**Audit date:** 2026-11-07  
**Artifact reviewed:** `ufc_quant_system_phase20.zip`  
**Verdict:** **OPERATIONAL WITH LIMITATIONS** (offline research CLI), **NOT PRODUCTION READY** for autonomous live prediction or betting workflows.

## Executive summary

The supplied archive is a Python command-line research application with historical data adapters, feature generation, logistic model, temporal/walk-forward backtesting, odds ROI simulation, event ingestion adapter, scheduler and HTML reports. It is not a browser webapp and has no frontend to interact with. The package contains a SQLite database but no full verified historical dataset or historical odds corpus.

The original tests passed 38/38. During hands-on CLI testing, the live UFC.com ingest command failed due environment DNS/network restrictions and surfaced a raw traceback. I fixed the CLI exception reporting and added a regression test. Final suite: **39/39 passed**. Compileall, demo report, JSON report and CLI help smoke checks passed. A coverage run reported **79% total statement coverage**.

Live event ingestion and real historical download could not be confirmed because outbound DNS/network is blocked in this runtime. The scheduler also could not be run: APScheduler is not installed in the audit environment; CLI gave its installation message. No real historical results/odds were loaded, so no real accuracy, calibration, or ROI metrics were calculated.

## Bug fixed

### Medium — raw traceback on external integration failures
- **Reproduction:** `python -m ufc_quant ingest-events --output /tmp/qa_live_card.json --timeout 3` with external DNS inaccessible.
- **Root cause:** CLI dispatch did not catch adapter/network exceptions.
- **Fix:** wrap dispatch with error handling; print a concise `error:` message and exit code 2 instead of traceback.
- **Regression test:** `tests/test_cli_error_handling.py::test_ingest_cli_network_error_is_concise`.
- **Verification:** regression test passes; live attempt now exits 2 with no traceback.

No other reproducible bugs were changed during this audit; the remaining items below are incomplete verification or product limitations, not claimed fixes.

## Functional coverage

See `FUNCTIONAL_COVERAGE_MATRIX.md` for module-by-module matrix. Key results:

- Offline demo and HTML report: passed.
- Unit suite: 39/39 passed.
- Compile checks: passed.
- Event page parser fixtures: covered by tests; live source unavailable.
- Historical data normalization and odds schema: fixture tests pass; no full corpus run.
- Feature engine and walk-forward logic: tested against fixtures; temporal caveat that input uses date-level ordering and same-date records rely on stable source order.
- Forecast-card outputs: fixture-tested, but probabilities remain uncalibrated and real model predictive validity is not demonstrated.
- ROI simulator: fixture-tested only; no verifiable time-stamped historical bookmaker prices, so no ROI result asserted.
- Scheduler: unverified live (APScheduler absent; scheduler is blocking).
- Browser UI: absent from the archive.

## Quantitative validation

| Metric | Result |
|---|---|
| Automated tests | 39 passed / 0 failed |
| Statement coverage | 79% |
| Live historical sample size | 0 (no data downloaded) |
| Accuracy / AUC / Brier / Log Loss / calibration | Not measured on real data |
| Brier Skill Score | Not measured on real data |
| ROI / yield / drawdown on real odds | Not measured |

Synthetic demo outputs are not used as evidence of real predictive performance.

## Reliability / environment

- `python -m ufc_quant demo`: passed; labels output synthetic.
- `python -m ufc_quant report --input sample_card.json --output ...`: passed.
- `python -m compileall -q ufc_quant tests`: passed.
- UFC.com event ingestion: blocked by DNS resolution in environment.
- Historical data download: not live-executed due same network constraint.
- Scheduler: APScheduler unavailable in environment; not run.
- Persistence: SQLite file and storage module exist, but complete restart workflow not verified.
- Security and performance: limited source review only; no complete CVE scan, load test or realistic dataset benchmark.

## Essential gaps before production

1. Execute live event ingest and history download from a network-enabled machine, validate source markup and provenance.
2. Add and verify an actual historical bout-statistics dataset and time-stamped pre-fight odds corpus.
3. Conduct robust date/event grouped backtesting, calibration and performance/ROI analyses on genuine out-of-sample data.
4. Add robust direct test coverage for model module, scheduler, empirical backtest and forecast-card edge cases.
5. Verify scheduler under installed APScheduler, including persistence/restart, failure retries and monitoring.
6. Verify persistence in an end-to-end restart test.
7. Perform full dependency security scan and resource/performance tests.
8. If a web UI is intended, it is a separate missing artifact; no frontend exists in this archive.

## Final verdict

**OPERATIONAL WITH LIMITATIONS** for local offline research, demo and fixture-backed analytical workflows. **NOT PRODUCTION READY** for unattended live UFC card prediction, calibrated probabilities, or betting/ROI decisions until real-source acquisition, historical dataset validation, scheduler runtime, security and performance are completed.
