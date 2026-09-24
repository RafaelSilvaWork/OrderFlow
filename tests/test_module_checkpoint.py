import json

from modules import module_checkpoint


def test_load_sem_checkpoint_retorna_none(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)

    assert module_checkpoint.load("extrator") is None


def test_save_e_load_ida_e_volta(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)

    module_checkpoint.save(
        "extrator",
        ["1", "2", "3"],
        {"criado_por": True},
        [{"requisicao": "1", "status": "Sem pedido emitido"}],
    )

    checkpoint = module_checkpoint.load("extrator")
    assert checkpoint["itens_originais"] == ["1", "2", "3"]
    assert checkpoint["extra"] == {"criado_por": True}
    assert checkpoint["resultados"] == [{"requisicao": "1", "status": "Sem pedido emitido"}]


def test_modulos_diferentes_usam_arquivos_separados(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)

    module_checkpoint.save("extrator", ["1"], {}, [{"requisicao": "1", "status": "ok"}])
    module_checkpoint.save("downloader", ["2"], {}, [{"requisicao": "2", "status": "ok"}])

    assert module_checkpoint.load("extrator")["itens_originais"] == ["1"]
    assert module_checkpoint.load("downloader")["itens_originais"] == ["2"]
    # limpar um não afeta o outro
    module_checkpoint.clear("extrator")
    assert module_checkpoint.load("extrator") is None
    assert module_checkpoint.load("downloader") is not None


def test_clear_remove_arquivo(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)
    module_checkpoint.save("pdf", ["1"], {}, [])

    assert module_checkpoint.load("pdf") is not None
    module_checkpoint.clear("pdf")
    assert module_checkpoint.load("pdf") is None


def test_clear_sem_arquivo_nao_quebra(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)

    module_checkpoint.clear("organizador")  # não deve levantar exceção


def test_load_com_json_corrompido_retorna_none(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)
    (tmp_path / "checkpoint_extrator.json").write_text("nao e json valido {{{", encoding="utf-8")

    assert module_checkpoint.load("extrator") is None


def test_pending_items_exclui_ja_processados():
    checkpoint = {
        "itens_originais": ["1", "2", "3", "4"],
        "resultados": [
            {"requisicao": "1", "status": "Sem pedido emitido"},
            {"requisicao": "2", "status": "Com pedido", "pedido": "900001"},
            {"requisicao": "2", "status": "Com pedido", "pedido": "900002"},
        ],
    }

    assert module_checkpoint.pending_items(checkpoint, "requisicao") == ["3", "4"]


def test_pending_items_funciona_com_outra_chave():
    checkpoint = {
        "itens_originais": ["900001", "900002"],
        "resultados": [{"pedido": "900001", "status": "Sucesso"}],
    }

    assert module_checkpoint.pending_items(checkpoint, "pedido") == ["900002"]


def test_pending_items_sem_nada_processado_retorna_tudo():
    checkpoint = {"itens_originais": ["1", "2"], "resultados": []}

    assert module_checkpoint.pending_items(checkpoint, "requisicao") == ["1", "2"]


def test_save_nunca_propaga_excecao_em_falha_de_disco(tmp_path, monkeypatch):
    bloqueio = tmp_path / "bloqueio"
    bloqueio.write_text("arquivo, nao pasta", encoding="utf-8")
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", bloqueio)

    module_checkpoint.save("extrator", ["1"], {}, [])  # não deve levantar exceção


def test_arquivo_gravado_e_json_valido(tmp_path, monkeypatch):
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)

    module_checkpoint.save("extrator", ["1"], {}, [{"requisicao": "1", "status": "Sem pedido emitido"}])

    dados = json.loads((tmp_path / "checkpoint_extrator.json").read_text(encoding="utf-8"))
    assert dados["itens_originais"] == ["1"]
