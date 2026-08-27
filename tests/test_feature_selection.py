import json

import modules.feature_selection as feature_selection
from main import build_tab_title


def test_load_enabled_modules_returns_defaults_when_file_missing(tmp_path, monkeypatch):
    selection_path = tmp_path / "module_selection.json"
    monkeypatch.setattr(feature_selection, "_selection_file_path", lambda: selection_path)

    selection = feature_selection.load_enabled_modules()

    assert selection["extrator"] is True
    assert selection["email"] is True
    assert selection_path.exists() is False


def test_load_enabled_modules_reads_selection_file(tmp_path, monkeypatch):
    selection_path = tmp_path / "module_selection.json"
    selection_path.write_text(json.dumps({"extrator": False, "email": True}), encoding="utf-8")
    monkeypatch.setattr(feature_selection, "_selection_file_path", lambda: selection_path)

    selection = feature_selection.load_enabled_modules()

    assert selection["extrator"] is False
    assert selection["email"] is True
    assert selection["pdf"] is True


def test_build_tab_title_marks_disabled_module():
    assert build_tab_title("extrator", False) == "🔒 📦 Extrator Inteligente"
    assert build_tab_title("extrator", True) == "📦 Extrator Inteligente"


def test_build_selection_for_modules_selects_only_requested_module():
    selection = feature_selection.build_selection_for_modules(["downloader"])

    assert selection["downloader"] is True
    assert selection["extrator"] is False
    assert selection["email"] is False
