import main


def test_build_module_state_active_when_widget_instantiated():
    state = main.FrameworkApp._build_module_state("extrator", "Extrator", object())

    assert state == {"key": "extrator", "label": "Extrator", "status": "ativo"}


def test_build_module_state_not_installed_when_no_widget_and_no_error(monkeypatch):
    monkeypatch.setattr(main, "IMPORT_ERRORS", {})

    state = main.FrameworkApp._build_module_state("downloader", "Downloader", None)

    assert state == {"key": "downloader", "label": "Downloader", "status": "nao_instalado"}


def test_build_module_state_error_when_import_failed(monkeypatch):
    monkeypatch.setattr(main, "IMPORT_ERRORS", {"OrcamentoDownloaderWidget": "traceback..."})

    state = main.FrameworkApp._build_module_state("downloader", "Downloader", None)

    assert state == {"key": "downloader", "label": "Downloader", "status": "erro"}
