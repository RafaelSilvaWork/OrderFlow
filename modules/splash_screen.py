"""Splash screen animada, sem bordas e com fundo transparente.

Mostrada antes do carregamento pesado do app (imports de bibliotecas
grandes, checagem de acesso, construção da janela principal) para dar
feedback visual imediato - sem ela, a tela fica em branco por alguns
segundos entre abrir o executável e a janela principal aparecer.

Suporta dois modos de animação do logotipo:
  - GIF/APNG animado (QMovie) - se você tiver um asset animado de verdade.
  - Onda por peças (padrão) - o logo é pré-recortado em pedaços (ver
    assets/branding/<marca>/logo_pecas/ e LOGO_PECAS_ORDEM em
    modules/branding.py) e cada peça é desenhada como um pixmap inteiro,
    íntegro, só deslocado verticalmente - nada é fatiado em tempo real,
    então a qualidade da imagem original é preservada (sem serrilhado).
    Cada peça oscila numa fase ligeiramente diferente da vizinha, dando a
    impressão de uma onda suave passando pelo logo - funciona tanto com uma
    palavra inteira soletrada letra por letra quanto com um ícone sozinho.
"""

import math
from collections.abc import Sequence
from pathlib import Path

from PyQt6.QtCore import QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QMovie, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

# Ordem de desenho das peças (esquerda pra direita) padrão - precisa bater
# com os nomes de arquivo gerados em assets/branding/<marca>/logo_pecas/ (ver
# docstring do módulo). Cada marca pode ter sua própria ordem/quantidade de
# peças (ver LOGO_PECAS_ORDEM em modules/branding.py) - esta é só o valor
# usado quando nenhuma ordem é passada explicitamente.
_PECAS_ORDENADAS = ["icone", "h", "a1", "p", "v", "i", "d", "a2"]


class _LogoOndaWidget(QWidget):
    """Desenha as peças pré-recortadas do logo, cada uma oscilando verticalmente
    numa fase própria - o efeito visual é uma onda suave passando pela palavra,
    sem nunca fatiar/distorcer a imagem em si (cada peça é um pixmap intacto).

    Funciona com qualquer quantidade de peças - de uma só (ícone sozinho,
    balançando) a uma palavra inteira letra por letra - por isso o incremento
    de fase é calculado na instância a partir de `ordem_pecas`, não fixo por
    classe.
    """

    _AMPLITUDE_PX = 11.0

    def __init__(self, pasta_pecas: str, ordem_pecas: Sequence[str] = _PECAS_ORDENADAS, parent=None):
        super().__init__(parent)
        self._INCREMENTO_FASE_POR_PECA = 2 * math.pi / len(ordem_pecas)
        self._pixmaps = [
            QPixmap(str(Path(pasta_pecas) / f"{nome}.png")) for nome in ordem_pecas
        ]
        largura = max((pm.width() for pm in self._pixmaps), default=0)
        altura = max((pm.height() for pm in self._pixmaps), default=0)
        self._margem = int(self._AMPLITUDE_PX) + 2
        self.setFixedSize(largura, altura + self._margem * 2)
        self._fase = 0.0

    def avancar_fase(self, incremento: float) -> None:
        self._fase = (self._fase + incremento) % (2 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for indice, pixmap in enumerate(self._pixmaps):
            angulo = self._fase + indice * self._INCREMENTO_FASE_POR_PECA
            deslocamento = round(self._AMPLITUDE_PX * math.sin(angulo))
            painter.drawPixmap(0, self._margem + deslocamento, pixmap)


class SplashScreen(QWidget):
    """Janela flutuante, sem moldura e com fundo transparente.

    Uso básico (logo em peças com onda, caso mais comum):
        splash = SplashScreen(caminho_logo="assets/branding/hapvida/logo_pecas")
        splash.show()
        ...
        splash.fechar_com_fade()

    Com um GIF/APNG animado de verdade em vez da onda:
        splash = SplashScreen(caminho_logo="assets/logo_animado.gif")
    """

    _DURACAO_FADE_MS = 350
    _INTERVALO_ONDA_MS = 30
    _INCREMENTO_FASE_POR_TICK = 0.10

    def __init__(self, caminho_logo: str, ordem_pecas: Sequence[str] = _PECAS_ORDENADAS):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen,
        )
        # Fundo 100% transparente - só o que for desenhado pelos widgets
        # filhos (logo + texto) aparece; a janela do SO fica invisível.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._movie: QMovie | None = None
        self._logo_wave: _LogoOndaWidget | None = None
        self._wave_timer: QTimer | None = None
        self._anim_fade: QPropertyAnimation | None = None
        self._lbl_logo_gif: QLabel | None = None

        if caminho_logo.lower().endswith((".gif", ".apng")):
            self._lbl_logo_gif = QLabel(self)
            self._lbl_logo_gif.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._lbl_logo_gif.setStyleSheet("background: transparent;")
            self._movie = QMovie(caminho_logo)
            self._lbl_logo_gif.setMovie(self._movie)
            self._movie.start()
            layout.addWidget(self._lbl_logo_gif, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            # Nesse modo, caminho_logo é a pasta com as peças pré-recortadas
            # (ver assets/branding/<marca>/logo_pecas/), não um arquivo único.
            self._logo_wave = _LogoOndaWidget(caminho_logo, ordem_pecas, parent=self)
            layout.addWidget(self._logo_wave, alignment=Qt.AlignmentFlag.AlignCenter)

        self.adjustSize()
        self._centralizar_na_tela()

    def _centralizar_na_tela(self) -> None:
        tela = self.screen() or QWidget().screen()
        if tela is None:
            return
        geometria_tela = tela.availableGeometry()
        x = geometria_tela.center().x() - self.width() // 2
        y = geometria_tela.center().y() - self.height() // 2
        self.move(x, y)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._logo_wave is not None and self._wave_timer is None:
            self._iniciar_onda()

    def _iniciar_onda(self) -> None:
        logo_wave = self._logo_wave
        assert logo_wave is not None
        self._wave_timer = QTimer(self)
        self._wave_timer.timeout.connect(
            lambda: logo_wave.avancar_fase(self._INCREMENTO_FASE_POR_TICK)
        )
        self._wave_timer.start(self._INTERVALO_ONDA_MS)

    def fechar_com_fade(self, ao_terminar=None) -> None:
        """Fecha a splash com um fade-out suave em vez de sumir abruptamente.

        `ao_terminar`, se informado, é chamado quando o fade termina (ex:
        para mostrar a janela principal só depois da splash sumir de vez).
        """
        efeito = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(efeito)
        self._anim_fade = QPropertyAnimation(efeito, b"opacity", self)
        self._anim_fade.setDuration(self._DURACAO_FADE_MS)
        self._anim_fade.setStartValue(1.0)
        self._anim_fade.setEndValue(0.0)

        def _finalizar():
            if self._movie is not None:
                self._movie.stop()
            if self._wave_timer is not None:
                self._wave_timer.stop()
            self.close()
            if ao_terminar is not None:
                ao_terminar()

        self._anim_fade.finished.connect(_finalizar)
        self._anim_fade.start()
