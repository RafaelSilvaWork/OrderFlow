import pytest

from modules import execution_history


@pytest.fixture(autouse=True)
def _historico_de_execucoes_isolado(tmp_path, monkeypatch):
    """Redireciona o histórico de execuções para uma pasta temporária em TODOS
    os testes.

    Vários widgets chamam record_execution() ao terminar uma execução
    (ex: CoupaExtractorWidget.automation_finished). Sem isso, rodar o pytest
    gravava execuções falsas no histórico REAL do usuário
    (%APPDATA%\\CoupaFramework\\historico_execucoes.json) - e como o arquivo
    guarda só as últimas 5 por módulo, as falsas empurravam as reais pra fora.

    Testes que precisam de um caminho específico (ex: test_execution_history)
    continuam podendo sobrescrever com o próprio monkeypatch.setattr.
    """
    monkeypatch.setattr(execution_history, "HISTORICO_EXECUCOES", tmp_path / "historico_execucoes.json")
