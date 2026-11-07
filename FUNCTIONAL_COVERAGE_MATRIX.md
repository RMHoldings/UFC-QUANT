# UFCQuant Phase 22 Functional Coverage Matrix (Audit)

Audit date: 2026-11-07. Refer to `UFCQUANT_PHASE22_AUDIT_REPORT.md` for evidence and detailed findings.

| Feature | Status | Coverage / evidence | Notes |
|---|---|---|---|
| Dashboard | Operational locally; deployed unverified | Static page source/build inspected | Browser verification blocked in runtime |
| API health | Fully operational locally | TestClient: 200 / status ok | Deployment URL not supplied |
| UFC upcoming event API | Operational but not verified live | Unit tests cover mocked successful and upstream-error paths | Actual upstream/deployed data not verified |
| Official upcoming event correctness | Not verified in application | Official UFC event sources checked independently | No live app URL to compare |
| Fight card display | Operational in code; browser unverified | Static frontend source examined | Source parsed card output not tested live |
| Fighter profiles | Missing | No web endpoint/page | Core audit requirement absent |
| Fighter stats | Missing | No web endpoint/page | No per-fighter validation possible |
| Matchup analysis | Missing | No web endpoint/page | No narrative/stat comparison implemented |
| Prediction engine UI/API | Missing in Phase 22 web adapter | Routes inspected | Demo report synthetic only |
| Model calibration / walk-forward metrics | Not verified | No real metric evaluation performed in this audit | Do not claim accuracy/ROI |
| CSV upload | Missing | API routes inspected | No upload route or UI |
| Demo report | Operational locally | TestClient validates HTML and DEMO marker | Synthetic inputs; not forecast |
| Report download | Partially implemented / absent | Button opens HTML blob in a tab | Explicit download control not found |
| SQLite integrity | Passed | PRAGMA integrity_check = ok | Not proof of deployment persistence |
| Scheduler / persistent deployment DB | Missing | Deployment guide limitation | Production infrastructure absent |
| Error handling | Operational with limitations | API tests and schema guard regression tests | Error messages deliberately avoid raw upstream details |
| CORS/deployment config | Requires configuration | Netlify/Render config reviewed | Placeholder domain must be replaced |
| Security scanner | Not run | pip_audit absent | No clean scan claim |
| Browser end-to-end | Blocked / not complete | Playwright navigation attempts rejected | Actual deployed URLs also not supplied |

## Regression tests added

- `test_upcoming_event_endpoint_rejects_invalid_event_schema`
- `test_upcoming_event_endpoint_rejects_non_object_fight_rows`
