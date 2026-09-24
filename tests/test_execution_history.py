import json

from modules import execution_history


def test_record_execution_grava_entrada(tmp_path, monkeypatch):
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", tmp_path / "historico_execucoes.json")

    execution_history.record_execution("extrator", success=True, summary="3 pedido(s) encontrado(s).")

    entradas = execution_history.load_history("extrator")
    assert len(entradas) == 1
    assert entradas[0]["success"] is True
    assert entradas[0]["summary"] == "3 pedido(s) encontrado(s)."
    assert "timestamp" in entradas[0]


def test_load_history_de_modulo_sem_execucoes_retorna_lista_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", tmp_path / "historico_execucoes.json")

    assert execution_history.load_history("extrator") == []


def test_mantem_so_as_ultimas_5_execucoes_mais_recente_primeiro(tmp_path, monkeypatch):
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", tmp_path / "historico_execucoes.json")

    for i in range(7):
        execution_history.record_execution("downloader", success=True, summary=f"execucao {i}")

    entradas = execution_history.load_history("downloader")
    assert len(entradas) == execution_history.MAX_ENTRIES_PER_MODULE
    assert entradas[0]["summary"] == "execucao 6"
    assert entradas[-1]["summary"] == "execucao 2"


def test_modulos_diferentes_nao_se_misturam(tmp_path, monkeypatch):
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", tmp_path / "historico_execucoes.json")

    execution_history.record_execution("extrator", success=True, summary="extrator ok")
    execution_history.record_execution("downloader", success=False, summary="downloader falhou")

    assert [e["summary"] for e in execution_history.load_history("extrator")] == ["extrator ok"]
    assert [e["summary"] for e in execution_history.load_history("downloader")] == ["downloader falhou"]


def test_arquivo_gravado_e_json_valido(tmp_path, monkeypatch):
    historico_path = tmp_path / "historico_execucoes.json"
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", historico_path)

    execution_history.record_execution("pdf", success=True, summary="2 pdf(s) gerado(s).")

    dados = json.loads(historico_path.read_text(encoding="utf-8"))
    assert dados["pdf"][0]["summary"] == "2 pdf(s) gerado(s)."


def test_record_execution_nunca_propaga_excecao_em_falha_de_disco(tmp_path, monkeypatch):
    """Best-effort de propósito - ver docstring de record_execution.

    Simula uma falha real de I/O criando um ARQUIVO no lugar onde o código
    precisaria criar um DIRETÓRIO (parent.mkdir) - isso levanta OSError na
    prática, sem precisar mockar internals do pathlib.
    """
    bloqueio = tmp_path / "bloqueio"
    bloqueio.write_text("isso e um arquivo, nao uma pasta", encoding="utf-8")
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", bloqueio / "historico_execucoes.json")

    execution_history.record_execution("organizador", success=True, summary="não deveria quebrar")
