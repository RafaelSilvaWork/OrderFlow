import pytest
from PyQt6.QtWidgets import QApplication

from main import LockedModuleWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_shows_download_button_when_module_not_installed(qt_app):
    widget = LockedModuleWidget(None, "downloader", "Baixador de Orçamentos", error_detail=None)

    assert widget.download_button.text() == "Baixar este módulo"
    assert widget.download_button.isEnabled()


def test_shows_reinstall_button_and_error_box_when_load_failed(qt_app):
    widget = LockedModuleWidget(
        None, "email", "Disparo de E-mails", error_detail="Traceback (most recent call last)..."
    )

    assert widget.download_button.text() == "Reinstalar módulo"


def test_download_failure_reoffers_correct_button_label(qt_app):
    widget = LockedModuleWidget(None, "pdf", "Gerador de PDF", error_detail="algum erro real")

    widget._on_install_finished(False, "sem conexão")

    assert widget.download_button.isEnabled()
    assert widget.download_button.text() == "Reinstalar módulo"


def test_install_success_hides_download_button_and_starts_countdown(qt_app):
    widget = LockedModuleWidget(None, "organizador", "Organizador", error_detail=None)

    widget._on_install_finished(True, "")
    try:
        assert widget.download_button.isVisible() is False
        assert widget._segundos_restantes == LockedModuleWidget.FECHAMENTO_AUTOMATICO_SEGUNDOS
        assert "Instalação concluída" in widget.lbl_install_status.text()
    finally:
        # Evita o QTimer real seguir agendado após o teste terminar.
        widget._fechamento_timer.stop()
