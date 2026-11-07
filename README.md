# UFC Main Card Quantitative Prediction System (MVP)

This is a runnable local starter project. It includes a transparent weighted model, logistic probability conversion, Monte Carlo outcome simulation, SQLite persistence, HTML report generation, and weekly scheduler.

## Important scope
- The event/fight ingestion adapter is deliberately marked as an integration point: UFC event cards and fighter statistics can change late and must be source-verified. This MVP does not pretend that live official-source ingestion or model calibration is already complete.
- The Monte Carlo engine executes 10,000 simulations when run. Its inputs are explicit parameters; estimates are only as sound as the supplied data and calibrated parameters.
- Production deployment (cloud hosting, email delivery, credentials, and official data ingestion verification) requires environment-specific setup.

## Run
Python 3.10+ recommended.

```bash
pip install -r requirements.txt
python -m ufc_quant demo
```

Generate report from a JSON fight card:
```bash
python -m ufc_quant report --input sample_card.json --output report.html
```

Run weekly scheduler (Saturday 09:00 Europe/Rome):
```bash
python -m ufc_quant schedule
```

Weights are in `config.json`. The demo is synthetic and clearly labeled.

## Phase 3: Historical collection and temporal backtest

Install dependencies with `pip install -r requirements.txt`.

Collect raw historical event/bout records (rate-limited public UFCStats pages):
`python -m ufc_quant.build_dataset --output ufcstats_raw_bouts.csv --max-pages 30`

Run a temporal holdout backtest on a CSV that has **pre-fight feature snapshots** and a binary `y` outcome:
`python -m ufc_quant.backtest_cli dataset.csv --features red_slpm_diff,red_td_def_diff,elo_diff --outcome y --date date`

The data collector outputs raw event/bout metadata, not an ML-ready outcome/features table. Create fighter history features using only bouts before the prediction timestamp; do not use post-fight stats. Minimum 30 rows is enforced, though substantially more historical examples are recommended. Metrics emitted: accuracy, Brier score, log loss, ROC AUC.

## Phase 4: Elo ratings

`ufc_quant.elo` computes a fighter's Elo rating snapshot **before** each fight and updates
ratings only after a known outcome. Default parameters: 1500 initial, K=32, scale=400,
neutral-site advantage 0. These are baseline choices, not yet tuned or validated.

`python -m ufc_quant.prepare_elo_dataset raw_bouts.csv --output elo_dataset.csv`

Outcome convention in this converter is y=1 for the first fighter/red row winning and y=0 for the second fighter/blue row winning. Raw scraped result markers can vary by page structure; inspect and validate the raw CSV before using it. The pipeline intentionally omits unrecognized outcomes rather than guessing.

## Phase 5: Leakage-safe pre-fight features

`ufc_quant.pre_fight_features` builds pre-fight snapshots for career win rate, last-3/last-5
form, rolling fight-stat averages, striking and takedown accuracy, and Elo. The code emits
features before updating with the current bout's target or post-fight stats, so those values
cannot flow into the same bout's feature row.

Input is a normalized CSV with columns `date`, `red_name`, `blue_name`, `y` (1 red win, 0
blue win, 0.5 draw), and optional per-bout stat columns named `red_sig_str_landed`,
`blue_sig_str_landed`, etc. Example:
`python -m ufc_quant.features_cli normalized_bout_stats.csv --output pre_fight_features.csv`

Important: Phase 5 supplies the temporal feature-engineering engine. The current Phase 3
UFCStats collector fetches event/bout metadata but does not yet parse each fight-detail page's
round-level stat tables into this normalized input. That live parser and historical data
validation remain the next integration task.

## Phase 6: UFCStats fight-details parser

The `ufc_quant.ufcstats_fight_parser` module parses the UFCStats totals table for the two
fighters, extracting significant/total strikes landed and attempted, takedowns, knockdowns,
submission attempts, reversals, and control time. Parsing warnings are retained.

Enable fight-detail requests in the historical collector:
`python -m ufc_quant.build_dataset --output ufcstats_with_totals.csv --max-pages 30 --include-stats --delay 2`

This option is more request-intensive because it visits each fight detail page. Use a respectful
delay and validate parse-warning counts and sample pages. HTML selectors can change; parser
tests use a local fixture and are not a substitute for a live-source smoke test. Fight totals
are post-fight outcomes/statistics and must only be rolled into the fighter history for future
bouts, as handled by Phase 5 feature engineering.

## Phase 7: Dataset quality audit

After collection, run:
`python -m ufc_quant.dataset_audit ufcstats_with_totals.csv --json dataset_qa.json --markdown dataset_qa.md`

The audit reports row and URL counts, duplicate bout IDs/URLs, column coverage and missingness,
numeric ranges, parse-warning frequency, and impossible landed/attempted stat pairs. It creates
JSON for machine processing and Markdown for review. It does not label a scraped dataset as
validated merely because the scraper completed.

## Phase 8: Offline end-to-end feature build and temporal backtest

Once a raw collection CSV exists (preferably with `--include-stats`), execute:
`python -m ufc_quant.pipeline ufcstats_with_totals.csv --features ufc_pre_fight_features.csv --report ufc_temporal_backtest.json`

The pipeline filters ambiguous outcomes, generates pre-fight snapshots in chronological order,
writes a feature CSV and trains a logistic regression temporal holdout. Missing feature values
are imputed with medians learned from training rows only. Draws and no-contests are excluded
from the binary target. Review UFCStats result labels and feature leakage before treating the
metrics as an estimate of predictive performance.

## Phase 9: Benchmarking and probability calibration diagnostics

The temporal report now compares the fitted feature logistic model against a transparent
Elo-only baseline on the same chronological test slice. It also provides reliability bins
(mean predicted probability vs observed win rate) to inspect calibration. Metrics are
descriptive for the held-out sample and are not betting recommendations or proof of edge.

## Phase 10: External historical dataset adapter

Normalize third-party historical bout CSVs to the project target schema:
`python -m ufc_quant.external_dataset source.csv --output normalized_historical_bouts.csv --summary normalization_summary.json`

The adapter requires date, both fighter names, and an explicit winner field. It maps winner to
binary target, excludes draws/NC and unresolved winner values, removes duplicate bout IDs,
and produces a transparent exclusion summary. It deliberately fails closed if winner data is
missing; a fight-list CSV containing only event, names, method, round and time is not sufficient
for outcome backtesting. Then invoke the existing `python -m ufc_quant.pipeline normalized_historical_bouts.csv`.


## Phase 11 — empirical backtest runner

After obtaining a historical CSV with explicit winner data and normalizing it with
`external_dataset.py`, run:

```bash
python -m ufc_quant.empirical_backtest normalized_historical_bouts.csv
```

This builds strictly pre-fight fighter-history/Elo snapshots and reports a chronological
holdout, model metrics, and Elo baseline comparison. It does **not** manufacture results
or stats absent from the source dataset. Actual accuracy only becomes empirical once a
real dataset is supplied and this command completes.
\n### Phase 12 — dataset schema compatibility\n\nThe external dataset adapter now directly recognizes the `01x3ATM3` UFC Stats CSV fields (`event_date_iso`, `header_fighter_a_name`, `header_fighter_b_name`, `header_winner_name`, `FightID_generated`). Dataset source: https://github.com/01x3ATM3/01x3ATM3-UFC_FIGHT_DATA_2013_TO_2025\n\n## Phase 14 — expanding-window walk-forward validation\n\nRun the sequential 5-fold walk-forward backtest on generated pre-fight features:\n\n```bash\npython -m ufc_quant.walk_forward ufc_empirical_features.csv --folds 5 --report ufc_walk_forward_report.json\n```\nEach fold fits only on earlier bouts, computes train-only medians, reports metrics and benchmarks Elo. Aggregate holdout predictions cover the entire post-initial-training period.\n\n## Phase 15 — odds / ROI simulation\n\nProvide a historical decimal odds CSV with date, red_name, blue_name, red_odds, blue_odds. Join against walk-forward predictions and run:\n\n```bash\npython -m ufc_quant.odds_backtest ufc_walk_forward_report.json historical_odds.csv --edge 0.03 --stake 0.01 --bankroll 1000\n```\nOverround-adjusted implied probabilities, edge and EV filters, fixed fractional stake (capped at 5%), bankroll trajectory, yield and drawdown are computed. No ROI claims are possible absent real historical odds.\n
## Phase 16 — source-backed upcoming event-card ingestion

The UFC.com adapter now fetches the event index, visits event detail pages, extracts a parseable event date/location and matchup names from recognizable fight-card markup, and selects the nearest dated upcoming card. It deduplicates index links and matchups, and fails closed when it cannot parse a card.

Fetch the nearest upcoming event card and save its source-backed manifest:

```bash
python -m ufc_quant ingest-events --output upcoming_event_card.json
```

Run the scheduled ingestion (Saturday 09:00 Europe/Rome):

```bash
python -m ufc_quant schedule --output upcoming_event_card.json
```

The scheduled task saves event metadata and matchup names only. It **does not** fabricate fighter feature snapshots, odds, or calibrated probabilities. To generate the model HTML report, the card must first be enriched with reliable `features_a` / `features_b` inputs and other report fields. UFC.com page markup can change; parser tests use local fixtures and a live-source test must be run in a network-enabled environment.

## Phase 17 — empirical upcoming-card forecasting

The `forecast-card` command connects a source-backed event card to a user-supplied
historical normalized CSV and fits a logistic model using leakage-safe pre-bout snapshots.
It requires explicit outcomes and at least 30 eligible historical bouts (configurable).
When the event date is available, only historical records with dates strictly before the
event date are used. Unknown fighter histories and imputed feature counts are reported
per matchup. Model probabilities are uncalibrated estimates—not betting advice or evidence
of a positive betting edge.

Example workflow (run from the project directory):

```bash
# Step 1: fetch an upcoming source-backed UFC.com card
python -m ufc_quant ingest-events --output upcoming_event_card.json

# Step 2: score it from a real normalized history CSV with date, red_name, blue_name, y
python -m ufc_quant forecast-card normalized_historical_bouts.csv upcoming_event_card.json --output forecast_card.json

# Step 3: generate the HTML report using the empirical probabilities
python -m ufc_quant report --input forecast_card.json --output forecast_report.html
```

The history CSV may include per-bout stats columns such as `red_sig_str_landed`,
`blue_sig_str_landed`, `red_td_landed`, and their attempted counterparts; absent stats
remain missing and are not fabricated. A meaningful empirical forecast still depends
on an adequately sized, audited, source-verified dataset and prior walk-forward
validation. This package does not bundle a verified complete historical UFC dataset.

## Phase 18 — reproducible history acquisition and stronger walk-forward diagnostics

Download the public third-party UFCStats-derived CSV and record its URL, download timestamp,
row count, schema, and SHA-256 checksum:

```bash
python -m ufc_quant download-history --output ufc_history_source.csv --provenance ufc_history_provenance.json
```

The downloader validates the required date, fighter-name, and winner columns and refuses to
replace the output if the downloaded file is malformed or unexpectedly small. The dataset is
third-party and is not represented as independently verified. Dataset page:
https://huggingface.co/datasets/01x3ATM3/UFC_FIGHT_DATA_2013_TO_2025

Then normalize, build leakage-safe pre-fight features, and run event-date-grouped validation:

```bash
python -m ufc_quant.external_dataset ufc_history_source.csv --output normalized_historical_bouts.csv --summary normalization_summary.json
python -m ufc_quant.empirical_backtest normalized_historical_bouts.csv --features empirical_pre_fight_features.csv --report empirical_backtest_report.json
python -m ufc_quant.walk_forward empirical_pre_fight_features.csv --folds 5 --report ufc_walk_forward_report.json
python -m ufc_quant.dataset_audit ufc_history_source.csv --json dataset_qa.json --markdown dataset_qa.md
```

Walk-forward test folds now keep all bouts with the same date together (avoiding same-event
split leakage), and add a constant 50/50 benchmark, Brier skill score, fold and aggregate
calibration bins, plus a seeded bootstrap confidence interval for Brier-score difference versus
50/50. Metrics remain descriptive; no profitability claim is warranted without separate
historical odds data and out-of-sample ROI evaluation. Live download was not run in the
restricted execution environment, so the source is wired but its live file integrity has not
been independently confirmed in this package build.

## Phase 19 — out-of-sample weight-class and market comparison

The expanding-window walk-forward report now preserves `weight_class` on each held-out prediction and adds descriptive subgroup metrics (n, accuracy, Brier, log loss, AUC) by weight class. Small groups are explicitly cautioned against over-interpretation.

For historical decimal odds joined to those held-out predictions, the ROI report now also evaluates normalized bookmaker fair probabilities on the matched sample and reports descriptive bet ROI / win rate by weight class, with sample-size cautions. These results are only meaningful when odds are time-stamped pre-fight and predictions are strictly out-of-sample; this software does not assert a profitable edge.

```bash
python -m ufc_quant.walk_forward empirical_pre_fight_features.csv --folds 5 --report ufc_walk_forward_report.json
python -m ufc_quant.odds_backtest ufc_walk_forward_report.json historical_odds.csv --edge 0.03 --stake 0.01 --bankroll 1000 --report ufc_roi_report.json
```

## Phase 20 — combined historical results + odds dataset adapter

A new adapter supports the public `complete_ufc_data.csv`-style schema (event date,
`fighter1`/`fighter2`, explicit `outcome`, favorite/underdog names and decimal odds).
It exports two files: a normalized bout history for pre-fight feature engineering and a
historical odds CSV compatible with the odds-aware evaluation. It does not infer a winner
from fighter order: only explicit recognized outcome labels are mapped; draws, no-contests,
and ambiguous labels are excluded and counted. Invalid/missing odds are separately tallied.

```bash
python -m ufc_quant.combined_dataset complete_ufc_data.csv \
  --normalized normalized_historical_bouts.csv \
  --odds historical_odds.csv \
  --summary combined_dataset_summary.json

python -m ufc_quant.empirical_backtest normalized_historical_bouts.csv \
  --features empirical_pre_fight_features.csv --report empirical_backtest_report.json
python -m ufc_quant.walk_forward empirical_pre_fight_features.csv --folds 5 \
  --report ufc_walk_forward_report.json
python -m ufc_quant.odds_backtest ufc_walk_forward_report.json historical_odds.csv \
  --edge 0.03 --stake 0.01 --bankroll 1000 --report ufc_roi_report.json
```

Dataset reference/schema description: https://github.com/jansen88/ufc-data . The source
README describes historical odds as scraped from betmma.tips, with gaps and name-matching
misses. Before interpreting ROI, inspect source timestamps and verify prices are pre-fight;
the adapter does not certify timing or completeness. The imported dataset's fighter profile
statistics are not used as pre-fight features because the snapshot timing may be post-event.

## Phase 20 — hands-on QA audit

The supplied Phase 20 archive was audited on 2026-11-07. See `FINAL_SYSTEM_AUDIT.md` and `FUNCTIONAL_COVERAGE_MATRIX.md` for the detailed audit verdict, coverage matrix, tested commands, known limitations, and the regression fix for concise CLI errors when external network adapters fail. Final offline suite: 39 tests passed; total coverage was 79%.

Live UFC.com acquisition and full historical-data downloads were not validated in the restricted audit environment (DNS/network unavailable). The scheduler was not run because APScheduler was not installed in that environment. No real accuracy, calibration, or ROI metrics are claimed. The archive is a CLI project, not a browser webapp.
