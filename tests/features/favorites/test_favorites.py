from sector_rotation.src.core.data import favorites
import pytest


def test_add_and_list_favorites(tmp_path, monkeypatch):
    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites.json")

    assert favorites.list_favorites("S&P 500") == []
    assert favorites.add_favorite("S&P 500", "aapl") is True
    assert favorites.add_favorite("S&P 500", "AAPL") is False

    assert favorites.list_favorites("S&P 500") == ["AAPL"]
    assert favorites.is_favorite("S&P 500", "AAPL") is True


def test_remove_and_toggle_favorites(tmp_path, monkeypatch):
    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites.json")

    assert favorites.toggle_favorite("NASDAQ", "MSFT") is True
    assert favorites.is_favorite("NASDAQ", "msft") is True

    assert favorites.remove_favorite("NASDAQ", "MSFT") is True
    assert favorites.is_favorite("NASDAQ", "MSFT") is False

    assert favorites.toggle_favorite("NASDAQ", "MSFT") is True
    assert favorites.toggle_favorite("NASDAQ", "MSFT") is False
    assert favorites.list_favorites("NASDAQ") == []


def test_invalid_file_content_is_tolerated(tmp_path, monkeypatch):
    favorites_file = tmp_path / "favorites.json"
    favorites_file.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(favorites, "FAVORITES_FILE", favorites_file)

    assert favorites.list_favorites("S&P 500") == []
    assert favorites.add_favorite("S&P 500", "NVDA") is True
    assert favorites.list_favorites("S&P 500") == ["NVDA"]


def test_list_all_and_total_count(tmp_path, monkeypatch):
    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites.json")

    favorites.add_favorite("S&P 500", "AAPL")
    favorites.add_favorite("NASDAQ", "MSFT")
    favorites.add_favorite("NASDAQ", "GOOG")

    all_favs = favorites.list_all_favorites()
    assert all_favs["S&P 500"] == ["AAPL"]
    assert all_favs["NASDAQ"] == ["MSFT", "GOOG"]
    assert favorites.total_favorites_count() == 3


def test_export_favorites_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites.json")

    favorites.add_favorite("S&P 500", "AAPL")
    favorites.add_favorite("NASDAQ", "MSFT")

    payload = favorites.export_favorites_settings()

    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites-imported.json")
    universe_count, ticker_count = favorites.import_favorites_settings(payload, merge=False)

    assert universe_count == 2
    assert ticker_count == 2
    assert favorites.list_all_favorites() == {"NASDAQ": ["MSFT"], "S&P 500": ["AAPL"]}


def test_import_favorites_settings_merge(tmp_path, monkeypatch):
    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites.json")

    favorites.add_favorite("NASDAQ", "MSFT")
    payload = '{"NASDAQ": ["GOOG", "MSFT"], "S&P 500": ["AAPL"]}'

    universe_count, ticker_count = favorites.import_favorites_settings(payload, merge=True)

    assert universe_count == 2
    assert ticker_count == 3
    assert favorites.list_all_favorites() == {"NASDAQ": ["MSFT", "GOOG"], "S&P 500": ["AAPL"]}


def test_import_favorites_settings_invalid_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(favorites, "FAVORITES_FILE", tmp_path / "favorites.json")

    with pytest.raises(ValueError, match="Invalid favorites JSON payload"):
        favorites.import_favorites_settings("not json")

    with pytest.raises(ValueError, match="Favorites payload must be a JSON object"):
        favorites.import_favorites_settings("[]")
