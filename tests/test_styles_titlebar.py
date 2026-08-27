import types

from modules.styles import aplicar_titlebar_escura


class _FakeWidget:
    def winId(self):
        return 12345


class _WidgetSemHandle:
    def winId(self):
        raise RuntimeError("sem handle nativo ainda")


def _fake_dwmapi(chamadas: list) -> types.SimpleNamespace:
    def DwmSetWindowAttribute(hwnd, attributo, valor_ref, tamanho):
        chamadas.append((hwnd, attributo))

    return types.SimpleNamespace(DwmSetWindowAttribute=DwmSetWindowAttribute)


def test_aplicar_titlebar_escura_chama_dwm_no_windows(monkeypatch):
    """No Windows, deve ativar o modo escuro e customizar cor de fundo/texto
    da barra de título (ver _DWMWA_* em modules/styles.py)."""
    chamadas: list = []
    monkeypatch.setattr("modules.styles.sys.platform", "win32")
    monkeypatch.setattr(
        "modules.styles.ctypes.windll", types.SimpleNamespace(dwmapi=_fake_dwmapi(chamadas)), raising=False
    )

    aplicar_titlebar_escura(_FakeWidget())

    assert len(chamadas) == 3
    assert all(hwnd == 12345 for hwnd, _ in chamadas)
    assert {attributo for _, attributo in chamadas} == {20, 35, 36}


def test_aplicar_titlebar_escura_nao_faz_nada_fora_do_windows(monkeypatch):
    chamadas: list = []
    monkeypatch.setattr("modules.styles.sys.platform", "linux")
    monkeypatch.setattr(
        "modules.styles.ctypes.windll", types.SimpleNamespace(dwmapi=_fake_dwmapi(chamadas)), raising=False
    )

    aplicar_titlebar_escura(_FakeWidget())

    assert chamadas == []


def test_aplicar_titlebar_escura_falha_silenciosa_sem_derrubar_o_app(monkeypatch):
    """Best-effort: se winId()/DWM falhar por qualquer motivo, não propaga -
    o app deve continuar funcionando normalmente, só sem o detalhe visual."""
    monkeypatch.setattr("modules.styles.sys.platform", "win32")

    aplicar_titlebar_escura(_WidgetSemHandle())  # não deve levantar
