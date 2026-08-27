import math
import time
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from modules.branding import LOGO_PECAS_DIR, LOGO_PECAS_ORDEM
from modules.splash_screen import SplashScreen

# Usa os assets/ordem da marca ATIVA (ver modules/branding.py) em vez de um
# caminho fixo - o repositório público não tem assets/branding/hapvida/, só
# assets/branding/generic/ (uma peça só), então um caminho hardcoded quebraria
# lá.
_PASTA_PECAS = str(Path(__file__).resolve().parents[1] / LOGO_PECAS_DIR)


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_sem_borda_e_fundo_transparente(qt_app):
    splash = SplashScreen(_PASTA_PECAS, LOGO_PECAS_ORDEM)

    assert bool(splash.windowFlags() & Qt.WindowType.FramelessWindowHint)
    assert splash.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def test_logo_em_pecas_usa_onda_nao_movie(qt_app):
    splash = SplashScreen(_PASTA_PECAS, LOGO_PECAS_ORDEM)

    assert splash._movie is None
    assert splash._logo_wave is not None
    assert len(splash._logo_wave._pixmaps) == len(LOGO_PECAS_ORDEM)
    assert all(not pm.isNull() for pm in splash._logo_wave._pixmaps)


def test_gif_usa_qmovie(qt_app, tmp_path):
    # Não precisa ser um GIF válido de verdade - só testamos que a extensão
    # decide o modo (QMovie), não o conteúdo do arquivo em si.
    caminho_gif = tmp_path / "logo_animado.gif"
    caminho_gif.write_bytes(b"GIF89a")

    splash = SplashScreen(str(caminho_gif))

    assert splash._movie is not None
    assert splash._logo_wave is None


def test_onda_so_comeca_depois_de_mostrar(qt_app):
    splash = SplashScreen(_PASTA_PECAS, LOGO_PECAS_ORDEM)
    assert splash._wave_timer is None

    splash.show()
    qt_app.processEvents()

    assert splash._wave_timer is not None
    assert splash._wave_timer.isActive()


def test_incremento_de_fase_distribui_a_onda_igualmente_entre_as_pecas(qt_app):
    # Onda "suave" (não alternada rígida): o incremento de fase entre peças
    # vizinhas é uma fração igual de volta completa, dividida pelo número de
    # peças da marca ativa - com só 1 peça (ex: marca genérica) a "onda" é a
    # própria peça balançando sozinha, então a checagem de "nunca sincroniza"
    # abaixo só faz sentido com 2+ peças (ex: marca com nome soletrado).
    logo = SplashScreen(_PASTA_PECAS, LOGO_PECAS_ORDEM)._logo_wave

    assert pytest.approx((2 * math.pi) / len(LOGO_PECAS_ORDEM)) == logo._INCREMENTO_FASE_POR_PECA
    if len(LOGO_PECAS_ORDEM) > 1:
        assert 0 < logo._INCREMENTO_FASE_POR_PECA < math.pi


def test_avancar_fase_muda_a_fase_e_e_ciclica(qt_app):
    splash = SplashScreen(_PASTA_PECAS, LOGO_PECAS_ORDEM)
    logo = splash._logo_wave

    fase_inicial = logo._fase
    logo.avancar_fase(0.18)

    assert logo._fase != fase_inicial

    # dar muitas voltas garante que o modulo (2*pi) mantem a fase no intervalo
    for _ in range(1000):
        logo.avancar_fase(0.18)
    assert 0 <= logo._fase < 6.30  # 2*pi ~ 6.2832


def test_fechar_com_fade_fecha_a_janela_e_chama_callback(qt_app):
    splash = SplashScreen(_PASTA_PECAS, LOGO_PECAS_ORDEM)
    splash.show()
    qt_app.processEvents()

    chamadas = []
    splash.fechar_com_fade(lambda: chamadas.append(True))

    # Espera o fade (curto, ver _DURACAO_FADE_MS) terminar de verdade,
    # processando eventos pra a QPropertyAnimation avançar.
    prazo = splash._DURACAO_FADE_MS / 1000 + 1.0
    inicio = time.perf_counter()
    while not chamadas and time.perf_counter() - inicio < prazo:
        qt_app.processEvents()
        time.sleep(0.01)

    assert chamadas == [True]
    assert not splash.isVisible()
    assert not splash._wave_timer.isActive()
