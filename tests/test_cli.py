import json

from guardedagent.cli import main


def test_default_run_refuses_to_publish(capsys):
    code = main(["What causes tides?"])
    out = capsys.readouterr().out
    assert code == 0
    assert "verdict : approved" in out
    assert "gate    : REFUSED" in out


def test_approve_flag_opens_the_gate(capsys):
    main(["What causes tides?", "--approve"])
    assert "gate    : APPROVED" in capsys.readouterr().out


def test_unanswerable_question_is_blocked(capsys):
    code = main(["What is the airspeed of an unladen swallow?"])
    assert code == 1
    assert "blocked" in capsys.readouterr().out


def test_tight_budget_halts_and_exits_nonzero(capsys):
    code = main(["What causes tides?", "--max-steps", "2"])
    assert code == 1
    assert "step limit" in capsys.readouterr().out


def test_trace_is_written(tmp_path, capsys):
    path = tmp_path / "trace.json"
    main(["What causes tides?", "--trace", str(path)])
    data = json.loads(path.read_text())
    assert data["span_count"] > 0
    assert "written" in capsys.readouterr().out
