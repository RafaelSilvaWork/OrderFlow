import modules as modules_pkg


def test_missing_own_module_file_is_treated_as_not_installed_not_as_error():
    # Simula um módulo removido pela instalação seletiva (arquivo .py ausente).
    # Deve retornar None silenciosamente, sem entrar em IMPORT_ERRORS - senão a
    # tela de módulo bloqueado mostra "erro interno" em vez de "não instalado".
    result = modules_pkg._safe_import(
        "TestOnlyMissingModuleWidget", "modules.this_module_file_does_not_exist_at_all"
    )

    assert result is None
    assert "TestOnlyMissingModuleWidget" not in modules_pkg.IMPORT_ERRORS


def test_missing_nested_dependency_is_recorded_as_a_real_error(tmp_path, monkeypatch):
    # Diferente do caso acima: aqui o próprio arquivo do módulo existe, mas ele
    # importa uma dependência que não está instalada - isso É um bug real
    # (ex: pacote pip faltando) e deve aparecer em IMPORT_ERRORS.
    broken_module = tmp_path / "broken_test_module_for_safe_import.py"
    broken_module.write_text("import this_dependency_does_not_exist_anywhere_xyz\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = modules_pkg._safe_import("TestOnlyBrokenModuleWidget", "broken_test_module_for_safe_import")

    assert result is None
    assert "TestOnlyBrokenModuleWidget" in modules_pkg.IMPORT_ERRORS
