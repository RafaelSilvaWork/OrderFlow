import json

import pytest
import requests

from modules import access_gate


@pytest.fixture(autouse=True)
def _gist_id_configurado(monkeypatch):
    """GIST_ID vem vazio por padrão (ver ACCESS_GATE_GIST_ID em
    modules/branding.py - só é preenchido em tempo de build via CI/secret).
    Sem isso, check_access() faria fail-open logo de cara (GIST_ID vazio) e
    nunca chegaria a exercitar a lógica real de leitura do gist testada
    abaixo - ver test_gist_id_vazio_libera_acesso_sem_chamar_rede pro
    comportamento sem essa fixture."""
    monkeypatch.setattr(access_gate, "GIST_ID", "test-gist-id")


def _fake_response(payload: dict):
    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    return _FakeResponse()


def _gist_payload(content: dict) -> dict:
    return {"files": {access_gate.GIST_FILE_NAME: {"content": json.dumps(content)}}}


def _mock_gist(monkeypatch, content: dict):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _fake_response(_gist_payload(content)))


def test_access_enabled_true_allows_access(monkeypatch):
    _mock_gist(monkeypatch, {"access_enabled": True, "blocked_users": []})
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_access_enabled_false_blocks_everyone(monkeypatch):
    _mock_gist(monkeypatch, {"access_enabled": False, "message": "Acesso revogado para teste."})
    allowed, message = access_gate.check_access()
    assert allowed is False
    assert message == "Acesso revogado para teste."


def test_access_enabled_false_uses_default_message_when_missing(monkeypatch):
    _mock_gist(monkeypatch, {"access_enabled": False})
    allowed, message = access_gate.check_access()
    assert allowed is False
    assert message == access_gate._DEFAULT_BLOCK_MESSAGE


def test_missing_access_enabled_field_fails_open(monkeypatch):
    _mock_gist(monkeypatch, {"blocked_users": []})
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_non_boolean_access_enabled_fails_open(monkeypatch):
    _mock_gist(monkeypatch, {"access_enabled": "no", "blocked_users": []})
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_network_error_fails_open(monkeypatch):
    def _raise(*a, **k):
        raise requests.exceptions.ConnectionError("sem rede")

    monkeypatch.setattr(requests, "get", _raise)
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_malformed_gist_content_fails_open(monkeypatch):
    payload = {"files": {access_gate.GIST_FILE_NAME: {"content": "not valid json"}}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: _fake_response(payload))
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_missing_gist_file_fails_open(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _fake_response({"files": {}}))
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_blocked_user_is_denied(monkeypatch):
    monkeypatch.setattr(access_gate, "current_username", lambda: "fulano.saiu")
    _mock_gist(monkeypatch, {"access_enabled": True, "blocked_users": ["fulano.saiu"], "message": "Bloqueado."})
    allowed, message = access_gate.check_access()
    assert allowed is False
    assert message == "Bloqueado."


def test_blocked_user_comparison_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(access_gate, "current_username", lambda: "Fulano.Saiu")
    _mock_gist(monkeypatch, {"access_enabled": True, "blocked_users": ["fulano.saiu"]})
    allowed, _ = access_gate.check_access()
    assert allowed is False


def test_user_not_in_blocked_list_is_allowed(monkeypatch):
    monkeypatch.setattr(access_gate, "current_username", lambda: "ciclano.ativo")
    _mock_gist(monkeypatch, {"access_enabled": True, "blocked_users": ["fulano.saiu"]})
    allowed, message = access_gate.check_access()
    assert allowed is True
    assert message == ""


def test_empty_username_is_never_matched_as_blocked(monkeypatch):
    monkeypatch.setattr(access_gate, "current_username", lambda: "")
    _mock_gist(monkeypatch, {"access_enabled": True, "blocked_users": [""]})
    allowed, _ = access_gate.check_access()
    assert allowed is True


def test_global_block_takes_priority_over_blocked_users_message(monkeypatch):
    monkeypatch.setattr(access_gate, "current_username", lambda: "qualquer.um")
    _mock_gist(monkeypatch, {"access_enabled": False, "blocked_users": [], "message": "Desligado para todos."})
    allowed, message = access_gate.check_access()
    assert allowed is False
    assert message == "Desligado para todos."


def test_gist_id_vazio_libera_acesso_sem_chamar_rede(monkeypatch):
    """Sem GIST_ID configurado (padrão de código-fonte - ver
    ACCESS_GATE_GIST_ID em modules/branding.py), check_access() libera direto,
    sem nem tentar a chamada de rede."""
    monkeypatch.setattr(access_gate, "GIST_ID", "")
    chamou_rede = []
    monkeypatch.setattr(requests, "get", lambda *a, **k: chamou_rede.append(1))

    allowed, message = access_gate.check_access()

    assert allowed is True
    assert message == ""
    assert chamou_rede == []
