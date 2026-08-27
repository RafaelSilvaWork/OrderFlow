import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules.pdf_generator import PdfGeneratorWorker
from modules.ui_pdf_generator import PedidoPdfGeneratorWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


def _make_widget(monkeypatch, tmp_path, texto_pedidos: str) -> PedidoPdfGeneratorWidget:
    # Impede que iniciar_geracao dispare o worker de verdade (abriria o Edge) -
    # só queremos exercitar a montagem da lista de pedidos e o log gerado.
    monkeypatch.setattr(PdfGeneratorWorker, "start", lambda self: None)

    widget = PedidoPdfGeneratorWidget(parent_framework=None)
    widget.pasta_saida = str(tmp_path)
    widget.txt_pedidos.setPlainText(texto_pedidos)
    return widget


def test_pedido_compartilhado_entre_requisicoes_gera_log_explicativo(qt_app, monkeypatch, tmp_path):
    widget = _make_widget(monkeypatch, tmp_path, "PED-100\tREQ-1\nPED-100\tREQ-2\nPED-200\tREQ-3")

    widget.iniciar_geracao()

    logs = widget.txt_logs.toPlainText()
    assert "aparecem em mais de uma requisição" in logs
    assert "PED-100" in logs
    assert "REQ-1" in logs
    assert "REQ-2" in logs


def test_sem_pedidos_compartilhados_nao_gera_log_extra(qt_app, monkeypatch, tmp_path):
    widget = _make_widget(monkeypatch, tmp_path, "PED-100\tREQ-1\nPED-200\tREQ-2")

    widget.iniciar_geracao()

    logs = widget.txt_logs.toPlainText()
    assert "aparecem em mais de uma requisição" not in logs


def test_pedido_compartilhado_por_tres_requisicoes(qt_app, monkeypatch, tmp_path):
    widget = _make_widget(
        monkeypatch, tmp_path, "PED-100\tREQ-1\nPED-100\tREQ-2\nPED-100\tREQ-3"
    )

    widget.iniciar_geracao()

    logs = widget.txt_logs.toPlainText()
    assert "1 pedido(s)" in logs
    assert "2 linha(s) a mais" in logs
    assert "REQ-1" in logs and "REQ-2" in logs and "REQ-3" in logs


def test_sem_pasta_destino_nao_inicia_e_avisa(qt_app, monkeypatch, tmp_path):
    # Sem essa checagem, PdfGeneratorWorker recebia pasta_saida="" e Path("")
    # vira o diretorio atual - os PDFs eram salvos ali silenciosamente.
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))
    monkeypatch.setattr(PdfGeneratorWorker, "start", lambda self: pytest.fail("worker nao deveria iniciar"))

    widget = PedidoPdfGeneratorWidget(parent_framework=None)
    widget.txt_pedidos.setPlainText("PED-100\tREQ-1")

    widget.iniciar_geracao()

    assert len(avisos) == 1
    assert widget.worker is None


def test_sem_pasta_destino_modo_automatico_nao_avisa(qt_app, monkeypatch, tmp_path):
    """No modo automatico (fluxo em cadeia), executar_automatico ja pula a
    aba antes de chamar iniciar_geracao - sem popup, so o log/sinal de aba
    pulada. Chamar iniciar_geracao diretamente (defesa extra) tambem so deve
    sair em silencio, sem popup, no modo automatico."""
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: avisos.append(a)))
    monkeypatch.setattr(PdfGeneratorWorker, "start", lambda self: pytest.fail("worker nao deveria iniciar"))

    widget = PedidoPdfGeneratorWidget(parent_framework=None)
    widget.txt_pedidos.setPlainText("PED-100\tREQ-1")

    widget.iniciar_geracao(modo_automatico=True)

    assert avisos == []
    assert widget.worker is None
