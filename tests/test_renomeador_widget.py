
import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from modules.services.renomeador_service import RenomeadorService
from modules.ui_renomeador import RenomeadorWidget


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    return app


def test_renomear_usa_coluna_de_status_correta(tmp_path, qt_app, monkeypatch):
    widget = RenomeadorWidget(parent_framework=None)
    widget.pasta = str(tmp_path)

    arquivo = tmp_path / "arquivo.pdf"
    arquivo.write_bytes(b"pdf")

    # Tabela agora tem 6 colunas (0: Arquivo, 1: ID Coupa, 2: Fornecedor, 3: Unid. Entrega, 4: Novo Nome, 5: Status)
    widget.table.setRowCount(1)
    widget.table.setItem(0, 0, QTableWidgetItem("arquivo.pdf"))
    widget.table.setItem(0, 4, QTableWidgetItem("novo.pdf"))
    widget.table.setItem(0, 5, QTableWidgetItem("\u2705 Pronto"))

    monkeypatch.setattr(widget, "salvar_historico", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    widget.renomear()

    assert widget.table.item(0, 5).text() == "\u2705 Renomeado"
    assert (tmp_path / "novo.pdf").exists()

def test_servico_gera_nome_arquivo_com_tamanho_limite(tmp_path):
    nome = RenomeadorService.gerar_nome_arquivo(
        "123456",
        "Fornecedor com nome extremamente longo para garantir truncamento",
        "Unidade de entrega muito longa para garantir truncamento",
    )

    assert nome.endswith(".pdf")
    assert len(nome) <= 180


def test_servico_renomeia_arquivo_e_cria_backup(tmp_path):
    origem = tmp_path / "origem.pdf"
    origem.write_bytes(b"conteudo")
    backup_dir = tmp_path / "Backup_Renomeamento"

    ok, status = RenomeadorService.renomear_arquivo(
        str(origem),
        str(tmp_path / "destino.pdf"),
        str(backup_dir),
    )

    assert ok is True
    assert status == "OK"
    assert not origem.exists()
    assert (tmp_path / "destino.pdf").exists()
    assert (backup_dir / "origem.pdf").exists()
