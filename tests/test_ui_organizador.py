from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules import module_checkpoint
from modules.ui_organizador import OrganizadorWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _checkpoint_isolado(tmp_path, monkeypatch):
    """Isola o checkpoint de execucao num diretorio temporario (ver
    modules/module_checkpoint.py, consultado no inicio de processar)."""
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)


def make_xlsx(path: Path, cabecalho: list):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(cabecalho)
    ws.append(["1", "2", "3"])
    wb.save(path)


def test_selecionar_planilha_popula_combos_com_colunas_reais(qt_app, tmp_path):
    planilha = tmp_path / "plan.xlsx"
    make_xlsx(planilha, ["Requisição", "Pedido Coupa", "Nome Fornecedor"])

    widget = OrganizadorWidget(parent_framework=None)
    widget._atualizar_colunas_detectadas(str(planilha))

    itens_rc = [widget.cbo_col_rc.itemText(i) for i in range(widget.cbo_col_rc.count())]
    assert itens_rc == ["Requisição", "Pedido Coupa", "Nome Fornecedor"]


def test_selecionar_planilha_preseleciona_coluna_quando_bate_com_o_padrao(qt_app, tmp_path):
    # minúsculo - deve casar sem diferenciar caixa. São os cabeçalhos que a
    # Aba 1 (Extrator Inteligente) gera de verdade: Requisição/Pedido/Fornecedor.
    planilha = tmp_path / "plan.xlsx"
    make_xlsx(planilha, ["requisição", "pedido", "fornecedor"])

    widget = OrganizadorWidget(parent_framework=None)
    widget._atualizar_colunas_detectadas(str(planilha))

    assert widget.cbo_col_rc.currentText() == "requisição"
    assert widget.cbo_col_po.currentText() == "pedido"
    assert widget.cbo_col_forn.currentText() == "fornecedor"


def test_colunas_sem_correspondencia_mantem_texto_digitado(qt_app, tmp_path):
    planilha = tmp_path / "plan.xlsx"
    make_xlsx(planilha, ["Coluna A", "Coluna B", "Coluna C"])

    widget = OrganizadorWidget(parent_framework=None)
    widget.cbo_col_rc.setEditText("Meu Texto Customizado")
    widget._atualizar_colunas_detectadas(str(planilha))

    # Nenhuma coluna da planilha bate com "Requisição" - o texto digitado
    # pelo usuário não deve ser apagado, só as opções do combo ganham as reais.
    assert widget.cbo_col_rc.currentText() == "Meu Texto Customizado"
    assert widget.cbo_col_rc.itemText(0) == "Coluna A"


def test_combo_de_coluna_continua_editavel_livremente(qt_app):
    widget = OrganizadorWidget(parent_framework=None)
    widget.cbo_col_rc.setEditText("QualquerCoisa")
    assert widget.cbo_col_rc.currentText() == "QualquerCoisa"


def test_planilha_ilegivel_nao_quebra_e_gera_log(qt_app, tmp_path):
    planilha = tmp_path / "corrompida.xlsx"
    planilha.write_bytes(b"nao e um xlsx de verdade")

    widget = OrganizadorWidget(parent_framework=None)
    widget._atualizar_colunas_detectadas(str(planilha))

    assert "Não foi possível ler as colunas" in widget.log_area.toPlainText()
    assert widget.cbo_col_rc.currentText() == "Requisição"

def _make_xlsx_rows(path: Path, rows: list):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["RC", "PO", "FORNECEDOR"])
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_oferecer_retomada_aceita_guarda_estado(qt_app, monkeypatch):
    module_checkpoint.save("organizador", [1, 2, 3], {}, [{"linha": 1}])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    widget = OrganizadorWidget(parent_framework=None)
    widget._oferecer_retomada_checkpoint()

    assert widget._resume_resultados_anteriores == [{"linha": 1}]
    assert "Retomando" in widget.log_area.toPlainText()


def test_oferecer_retomada_recusa_descarta_checkpoint(qt_app, monkeypatch):
    module_checkpoint.save("organizador", [1, 2], {}, [])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    widget = OrganizadorWidget(parent_framework=None)
    widget._oferecer_retomada_checkpoint()

    assert widget._resume_resultados_anteriores is None
    assert module_checkpoint.load("organizador") is None


def test_processar_automatico_nunca_pergunta(qt_app, monkeypatch, tmp_path):
    module_checkpoint.save("organizador", [1], {}, [{"linha": 1}])
    perguntou = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: perguntou.append(1))

    widget = OrganizadorWidget(parent_framework=None)
    widget.ent_destino.setText("")  # forca falha rapida (sem pasta destino), sem side effects
    widget.processar(modo_automatico=True)

    assert perguntou == []


def test_processar_retomada_pula_linha_ja_processada(qt_app, monkeypatch, tmp_path):
    propostas = tmp_path / "propostas"
    destino = tmp_path / "destino"
    propostas.mkdir()
    destino.mkdir()
    planilha = tmp_path / "plan.xlsx"
    _make_xlsx_rows(planilha, [["RC001", "PO001", "Fornecedor A"], ["RC002", "PO002", "Fornecedor B"]])
    (propostas / "RC001_orcamento.pdf").write_bytes(b"pdf")
    (propostas / "RC002_orcamento.pdf").write_bytes(b"pdf")

    module_checkpoint.save("organizador", [1, 2], {}, [{"linha": 1}])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    widget = OrganizadorWidget(parent_framework=None)
    widget.ent_propostas.setText(str(propostas))
    widget.ent_destino.setText(str(destino))
    widget.ent_planilha.setText(str(planilha))
    widget.cbo_col_rc.setEditText("RC")
    widget.cbo_col_po.setEditText("PO")
    widget.cbo_col_forn.setEditText("FORNECEDOR")

    widget.processar()

    assert not (destino / "Fornecedor A").exists()
    assert (destino / "Fornecedor B").is_dir()

