import json

from guardedagent.trace import Trace


def test_span_records_duration_and_attributes():
    trace = Trace("r1")
    with trace.span("work", "node", foo="bar") as span:
        span.attributes["extra"] = 1
    assert len(trace.spans) == 1
    assert trace.spans[0].attributes == {"foo": "bar", "extra": 1}
    assert trace.spans[0].ended_at is not None


def test_exception_is_recorded_and_re_raised():
    trace = Trace("r2")
    try:
        with trace.span("boom", "tool"):
            raise ValueError("nope")
    except ValueError:
        pass
    assert trace.spans[0].error == "ValueError: nope"


def test_save_roundtrip(tmp_path):
    trace = Trace("r3")
    with trace.span("a", "node"):
        pass
    path = trace.save(tmp_path / "t.json")
    data = json.loads(path.read_text())
    assert data["run_id"] == "r3" and data["span_count"] == 1


def test_summary_counts_by_kind():
    trace = Trace("r4")
    with trace.span("a", "node"):
        pass
    with trace.span("b", "tool"):
        pass
    assert "node=1" in trace.summary() and "tool=1" in trace.summary()
