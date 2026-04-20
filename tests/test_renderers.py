import pandas as pd

from sector_rotation.src.renderers import render_data_card, safe_format


def test_safe_format_numeric_and_nan():
    assert safe_format(3.14159) == "3.14"
    assert safe_format(float("nan")) == "N/A"


def test_render_data_card_calls_chart(monkeypatch):
    calls = []

    monkeypatch.setattr("sector_rotation.src.renderers.st.subheader", lambda title: calls.append(("subheader", title)))
    monkeypatch.setattr("sector_rotation.src.renderers.st.write", lambda *args, **kwargs: calls.append(("write", args)))
    monkeypatch.setattr("sector_rotation.src.renderers.render_chart", lambda *args, **kwargs: calls.append(("chart", args)))

    close = pd.Series([1, 2, 3, 4, 5])
    volume = pd.Series([10, 20, 30, 40, 50])

    render_data_card("My Title", close, volume, subtitle="sub", metadata="meta")

    assert ("subheader", "My Title") in calls
    assert any(call[0] == "chart" for call in calls)
