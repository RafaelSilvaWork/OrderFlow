from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from modules.ui_organizador import OrganizadorWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


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
