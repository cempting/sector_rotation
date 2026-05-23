from sector_rotation.src.core.analytics import app_control


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_open_industry_stocks_sets_navigation_state(monkeypatch):
    session_state = _SessionState(selected_stock="AAPL", nav_stock="AAPL")
    monkeypatch.setattr(app_control.st, "session_state", session_state)

    app_control.open_industry_stocks("Technology", "Software")

    assert session_state["nav_feature"] == "browse"
    assert session_state["view"] == "industry_stocks"
    assert session_state["selected_sector"] == "Technology"
    assert session_state["nav_sector"] == "Technology"
    assert session_state["selected_industry"] == "Software"
    assert session_state["nav_industry"] == "Software"
    assert "selected_stock" not in session_state
    assert "nav_stock" not in session_state


def test_open_industry_stocks_without_sector_clears_sector_nav(monkeypatch):
    session_state = _SessionState(selected_sector="Technology", nav_sector="Technology")
    monkeypatch.setattr(app_control.st, "session_state", session_state)

    app_control.open_industry_stocks(None, "Semiconductors")

    assert "selected_sector" not in session_state
    assert "nav_sector" not in session_state
    assert session_state["selected_industry"] == "Semiconductors"
    assert session_state["nav_industry"] == "Semiconductors"


def test_nav_to_industry_stocks_button_uses_default_key(monkeypatch):
    captured = {}

    def fake_button(label, **kwargs):
        captured["label"] = label
        captured.update(kwargs)
        return False

    monkeypatch.setattr(app_control.st, "button", fake_button)

    app_control.nav_to_industry_stocks_button("Energy", "Oil & Gas")

    assert captured["label"] == "View Stocks"
    assert captured["key"] == "stocks-Energy-Oil & Gas"
    assert captured["on_click"] is app_control.open_industry_stocks
    assert captured["args"] == ("Energy", "Oil & Gas")


def test_nav_to_industry_stocks_button_honors_custom_key(monkeypatch):
    captured = {}

    def fake_button(label, **kwargs):
        captured.update(kwargs)
        return False

    monkeypatch.setattr(app_control.st, "button", fake_button)

    app_control.nav_to_industry_stocks_button("Finance", "Banks", key="custom-key")

    assert captured["key"] == "custom-key"
