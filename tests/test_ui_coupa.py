from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules import module_checkpoint
from modules.coupa_scraper import AutomationWorker
from modules.ui_coupa import CoupaExtractorWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(qt_app, tmp_path):
    # Isola de coupa_profiles.json real (dados sensíveis do usuário).
    with patch("modules.config.CONFIG_FILE", tmp_path / "perfis_teste.json"):
        return CoupaExtractorWidget(parent_framework=None)


@pytest.fixture(autouse=True)
def _checkpoint_isolado(tmp_path, monkeypatch):
    """Isola o checkpoint de execução num diretório temporário (ver
    modules/module_checkpoint.py, consultado no início de
    open_edge_for_login)."""
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)


def test_load_selected_profile_lista_campos_ativos(widget):
    widget.profiles = {
        "Perfil A": {"config": {"criado_por": True, "solicitado_por": False, "emails": True, "destino": False}}
    }

    widget.load_selected_profile("Perfil A")

    assert widget.lbl_config_status.text() == "Campos ativos: Criado Por, E-mails"


def test_load_selected_profile_nenhum_campo_ativo(widget):
    widget.profiles = {"Vazio": {"config": {}}}

    widget.load_selected_profile("Vazio")

    assert widget.lbl_config_status.text() == "Campos ativos: Nenhum"


def test_load_selected_profile_ignora_nome_desconhecido(widget):
    widget.profiles = {}
    widget.lbl_config_status.setText("original")

    widget.load_selected_profile("nao existe")

    assert widget.lbl_config_status.text() == "original"


def test_open_edge_for_login_exige_perfil_selecionado(widget):
    widget.combo_profiles.clear()
    widget.txt_req_list.setPlainText("123")

    widget.open_edge_for_login()

    assert "Selecione um perfil" in widget.txt_logs.toPlainText()


def test_open_edge_for_login_exige_requisicoes(widget):
    widget.profiles = {"Perfil A": {"config": {}}}
    widget.combo_profiles.clear()
    widget.combo_profiles.addItem("Perfil A")
    widget.txt_req_list.clear()

    widget.open_edge_for_login()

    assert "Insira requisi" in widget.txt_logs.toPlainText()


def test_open_edge_for_login_remove_requisicoes_repetidas(widget, monkeypatch):
    # Impede que o worker de verdade suba (abriria o Edge) - só queremos
    # verificar a lista deduplicada e o log de aviso.
    monkeypatch.setattr(AutomationWorker, "start", lambda self: None)
    widget.profiles = {"Perfil A": {"config": {}}}
    widget.combo_profiles.clear()
    widget.combo_profiles.addItem("Perfil A")
    widget.txt_req_list.setPlainText("111\n222\n111\n333\n222\n222")

    widget.open_edge_for_login()

    assert widget.worker.requisicoes == ["111", "222", "333"]
    logs = widget.txt_logs.toPlainText()
    assert "repetida" in logs
    # 111 aparecia 2x (1 ignorada) e 222 aparecia 3x (2 ignoradas) - a
    # contagem tem que refletir só as repetições extras, não o total de
    # ocorrências, senão parece que a requisição inteira foi descartada.
    assert "111 (1 ocorrência ignorada)" in logs
    assert "222 (2 ocorrências ignoradas)" in logs


def test_open_edge_for_login_sem_repeticao_nao_gera_aviso(widget, monkeypatch):
    monkeypatch.setattr(AutomationWorker, "start", lambda self: None)
    widget.profiles = {"Perfil A": {"config": {}}}
    widget.combo_profiles.clear()
    widget.combo_profiles.addItem("Perfil A")
    widget.txt_req_list.setPlainText("111\n222\n333")

    widget.open_edge_for_login()

    assert widget.worker.requisicoes == ["111", "222", "333"]
    assert "repetida" not in widget.txt_logs.toPlainText()


def test_automation_finished_sem_resultados_limpa_tabela(widget):
    widget.tbl_results.setRowCount(3)

    widget.automation_finished([])

    assert widget.tbl_results.rowCount() == 0
    assert widget.last_results == []


def test_automation_finished_popula_tabela_e_habilita_botoes(widget, monkeypatch):
    armazenados = {}
    monkeypatch.setattr(
        "modules.ui_coupa.DataBus.store_extraction_results",
        lambda results: armazenados.setdefault("results", results),
    )
    widget.chk_aba2.setChecked(False)
    widget.chk_aba3.setChecked(False)
    widget.chk_aba4.setChecked(False)
    widget.chk_aba5.setChecked(False)
    widget.chk_aba6.setChecked(False)

    resultados = [
        {
            "requisicao": "1", "pedido": "P1", "fornecedor": "ACME",
            "criado_por": "Fulano", "localidade": "SP", "status": "Com pedido",
        },
        {"requisicao": "2", "erro": "falhou"},
    ]

    widget.automation_finished(resultados)

    assert widget.last_results == resultados
    assert armazenados["results"] == resultados
    assert widget.btn_excel.isEnabled() is True
    assert widget.btn_open_edge.isEnabled() is True
    assert widget.tbl_results.rowCount() == 2
    # A tabela ordena ao reativar setSortingEnabled(True), então a posição
    # das linhas não é garantida - busca pelo nº da requisição (coluna 0).
    status_por_requisicao = {
        widget.tbl_results.item(row, 0).text(): widget.tbl_results.item(row, 5).text()
        for row in range(widget.tbl_results.rowCount())
    }
    assert status_por_requisicao == {"1": "Com pedido", "2": "Erro"}
    assert "desabilitado" in widget.lbl_fluxo_status.text()


def test_on_progress_mostra_barra_sem_agendar_timer_abaixo_de_100(widget):
    widget._on_progress(50)

    assert widget.progress_bar.isHidden() is False
    assert getattr(widget, "_progress_hide_timer", None) is None


def test_on_progress_agenda_timer_ao_completar(widget):
    widget._on_progress(100)

    assert widget._progress_hide_timer is not None
    assert widget._progress_hide_timer.isSingleShot() is True


def test_open_edge_for_login_sem_checkpoint_nao_pergunta_nada(widget, monkeypatch):
    perguntou = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: perguntou.append(1))
    monkeypatch.setattr(AutomationWorker, "start", lambda self: None)
    widget.profiles = {"Perfil A": {"config": {}}}
    widget.combo_profiles.clear()
    widget.combo_profiles.addItem("Perfil A")
    widget.txt_req_list.setPlainText("111")

    widget.open_edge_for_login()

    assert perguntou == []
    assert widget.worker.requisicoes_originais is None
    assert widget.worker.resultados_anteriores is None


def test_oferecer_retomada_aceita_preenche_lista_e_guarda_estado(widget, monkeypatch):
    module_checkpoint.save(
        "extrator",
        ["111", "222", "333"],
        {},
        [{"requisicao": "111", "status": "Sem pedido emitido"}],
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    widget._oferecer_retomada_checkpoint()

    assert widget.txt_req_list.toPlainText() == "222\n333"
    assert widget._resume_requisicoes_originais == ["111", "222", "333"]
    assert widget._resume_resultados_anteriores == [{"requisicao": "111", "status": "Sem pedido emitido"}]
    assert "Retomando" in widget.txt_logs.toPlainText()


def test_oferecer_retomada_recusa_descarta_checkpoint(widget, monkeypatch):
    module_checkpoint.save("extrator", ["111", "222"], {}, [])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    widget._oferecer_retomada_checkpoint()

    assert widget._resume_requisicoes_originais is None
    assert widget._resume_resultados_anteriores is None
    assert module_checkpoint.load("extrator") is None


def test_open_edge_for_login_retomada_passa_estado_pro_worker(widget, monkeypatch):
    module_checkpoint.save(
        "extrator",
        ["111", "222"],
        {},
        [{"requisicao": "111", "status": "Sem pedido emitido"}],
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(AutomationWorker, "start", lambda self: None)
    widget.profiles = {"Perfil A": {"config": {}}}
    widget.combo_profiles.clear()
    widget.combo_profiles.addItem("Perfil A")

    widget.open_edge_for_login()

    assert widget.worker.requisicoes == ["222"]
    assert widget.worker.requisicoes_originais == ["111", "222"]
    assert widget.worker.resultados_anteriores == [{"requisicao": "111", "status": "Sem pedido emitido"}]
