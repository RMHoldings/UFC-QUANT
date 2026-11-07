import argparse
import json
from pathlib import Path

from .report import build_report
from .scheduler import ingest_upcoming_card, run_scheduler


def main():
    parser = argparse.ArgumentParser(description="UFCQuant local research and event-card tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="Generate report from synthetic demo inputs")

    report = sub.add_parser("report", help="Generate a model report from a feature-enriched JSON card")
    report.add_argument("--input", required=True)
    report.add_argument("--output", required=True)

    history = sub.add_parser("download-history", help="Download public UFCStats-derived historical CSV and provenance metadata")
    history.add_argument("--output", default="ufc_history_source.csv")
    history.add_argument("--provenance", default="ufc_history_provenance.json")
    history.add_argument("--url", default=None)
    history.add_argument("--timeout", type=float, default=60)

    ingest = sub.add_parser("ingest-events", help="Fetch nearest upcoming UFC.com event and save its sourced fight-card manifest")
    ingest.add_argument("--output", default="upcoming_event_card.json")
    ingest.add_argument("--timeout", type=float, default=20)

    schedule = sub.add_parser("schedule", help="Run Saturday 09:00 Europe/Rome event-card ingestion")
    schedule.add_argument("--output", default="upcoming_event_card.json")

    forecast = sub.add_parser("forecast-card", help="Score a sourced upcoming card using supplied historical bout outcomes")
    forecast.add_argument("historical_csv", help="Normalized historical CSV with date, red_name, blue_name, y")
    forecast.add_argument("card_json", help="Upcoming sourced event card JSON")
    forecast.add_argument("--output", default="forecast_card.json")
    forecast.add_argument("--min-bouts", type=int, default=30)

    args = parser.parse_args()
    config_path = Path("config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    try:
        if args.cmd == "demo":
            card = json.loads(Path("sample_card.json").read_text(encoding="utf-8"))
            output = build_report(card, config)
            Path("demo_report.html").write_text(output, encoding="utf-8")
            print("Created demo_report.html (synthetic inputs only).")
        elif args.cmd == "report":
            card = json.loads(Path(args.input).read_text(encoding="utf-8"))
            output = build_report(card, config)
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Created {args.output}")
        elif args.cmd == "forecast-card":
            from .forecast_card import predict_card
            result = predict_card(args.historical_csv, args.card_json, args.output, args.min_bouts)
            print(json.dumps(result, indent=2))
        elif args.cmd == "download-history":
            from .download_history import download_history, DEFAULT_URL
            result = download_history(args.output, args.provenance, args.url or DEFAULT_URL, args.timeout)
            print(json.dumps(result, indent=2))
        elif args.cmd == "ingest-events":
            from .ingest_ufc_com import fetch_next_upcoming_event
            card = fetch_next_upcoming_event(timeout=args.timeout)
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Saved {len(card['fights'])} sourced matchups for {card['event']['name']} to {path}.")
            print("Forecast skipped: fighter feature snapshots and calibrated inputs are not supplied.")
        else:
            run_scheduler(output=args.output)
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        parser.exit(2, f"error: {exc}\n")
    except Exception as exc:
        # External adapters can raise requests/network exceptions; keep CLI failures actionable.
        parser.exit(2, f"error: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
