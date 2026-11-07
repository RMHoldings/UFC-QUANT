import pytest


def test_ingest_cli_network_error_is_concise(monkeypatch, capsys):
    import sys
    from ufc_quant import __main__ as cli

    def fail_fetch(timeout=20):
        raise RuntimeError("external source unavailable")

    monkeypatch.setattr(sys, "argv", ["ufc_quant", "ingest-events", "--timeout", "1"])
    monkeypatch.setattr("ufc_quant.ingest_ufc_com.fetch_next_upcoming_event", fail_fetch)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "error: external source unavailable" in captured.err
    assert "Traceback" not in captured.err
