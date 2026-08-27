"""Tema dark/tech do framework.

Folha de estilo global (QSS) + uns utilitários pra manter a aparência
consistente em todas as abas. Visual escuro, inspirado em VS Code / GitHub Dark.

Paleta de Cores:
  - Background App:     #0d1117  (fundo principal)
  - Background Painel:  #161b22  (cards, grupos, inputs)
  - Background Elevado: #1c2128  (hover / elementos elevados)
  - Border:             #30363d
  - Border Hover:       #3d444d
  - Accent Primary:     #58a6ff  (azul - ações padrão / foco)
  - Accent Primary Dk:  #388bfd
  - Accent Cyan:        #22d3ee  (detalhes / progresso)
  - Success:            #3fb950  (verde)
  - Warning:             #d29922 (âmbar)
  - Danger:              #f85149 (vermelho)
  - Text Primary:        #e6edf3
  - Text Secondary:      #8b949e
  - Text Muted:          #6e7681

Uso do helper `set_status`:
    from modules.styles import set_status
    set_status(self.lbl_status, "success")   # também: "error", "warning", "muted", "normal"
"""

import contextlib
import ctypes
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QScrollArea, QWidget

from modules.styles_qss.base import QSS_BASE
from modules.styles_qss.buttons import QSS_BUTTONS
from modules.styles_qss.inputs import QSS_INPUTS
from modules.styles_qss.labels import QSS_LABELS
from modules.styles_qss.widgets import QSS_WIDGETS

# DWM (Desktop Window Manager) attributes usados por aplicar_titlebar_escura -
# não vêm expostos no ctypes/wintypes padrão, então são os IDs numéricos
# oficiais da API do Windows (dwmapi.h).
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_CAPTION_COLOR = 35  # Windows 11 22000+
_DWMWA_TEXT_COLOR = 36  # Windows 11 22000+


def _colorref(hex_cor: str) -> int:
    """Converte "rrggbb" pro formato COLORREF do Windows (0x00BBGGRR)."""
    r, g, b = int(hex_cor[0:2], 16), int(hex_cor[2:4], 16), int(hex_cor[4:6], 16)
    return (b << 16) | (g << 8) | r


def aplicar_titlebar_escura(widget: QWidget) -> None:
    """Deixa a barra de título NATIVA do Windows escura, combinando com o
    tema dark do app (ver APP_STYLESHEET) - por padrão o Windows desenha uma
    barra de título clara, destoando bastante do resto da janela.

    Chama a API do DWM (Desktop Window Manager) direto via ctypes - não tem
    equivalente no Qt. Em janelas onde o Windows 11 aceita cor customizada
    (build 22000+), usa a cor de fundo/texto do próprio tema; senão cai só
    no modo escuro genérico do Windows (ainda bem melhor que o padrão claro).

    Best-effort: em qualquer falha (Windows mais antigo, ambiente sem DWM,
    SO diferente de Windows etc.) simplesmente não faz nada - o app segue
    funcionando normalmente, só sem esse detalhe visual.
    """
    if sys.platform != "win32":
        return

    with contextlib.suppress(Exception):
        hwnd = int(widget.winId())
        dwmapi = ctypes.windll.dwmapi  # type: ignore[attr-defined]

        def _set_attr(attributo: int, valor: int) -> None:
            dwmapi.DwmSetWindowAttribute(
                hwnd, attributo, ctypes.byref(ctypes.c_int(valor)), ctypes.sizeof(ctypes.c_int)
            )

        _set_attr(_DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
        _set_attr(_DWMWA_CAPTION_COLOR, _colorref("0d1117"))  # Background App
        _set_attr(_DWMWA_TEXT_COLOR, _colorref("e6edf3"))  # Text Primary


def set_status(widget: QWidget, status: str, text: str | None = None) -> None:
    """Aplica um estado visual (cor/estilo) a um QLabel via propriedade QSS.

    Substitui o padrão antigo de `label.setStyleSheet("color: ...")`, que
    fixava cores incompatíveis com o tema escuro. Em vez disso, define a
    propriedade dinâmica `status` e força o Qt a reprocessar o estilo.

    Args:
        widget: o QLabel (ou outro QWidget) a estilizar.
        status: um de "success", "error", "warning", "muted", "normal", "accent".
        text: se informado, também atualiza o texto do widget.
    """
    if text is not None and hasattr(widget, "setText"):
        widget.setText(text)
    widget.setProperty("status", status)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()


def scrollable(content: QWidget) -> QScrollArea:
    """Envolve um QWidget (geralmente um painel com vários QGroupBox) em uma
    QScrollArea transparente.

    Sem isso, quando a janela não está maximizada e o conteúdo de uma aba
    é mais alto do que o espaço disponível, o Qt pode ser forçado a
    espremer widgets abaixo do seu tamanho mínimo — o que causa
    sobreposição visual (botões/labels "grudados" uns nos outros) em vez de
    simplesmente cortar. Com a QScrollArea, o painel ganha uma barra de
    rolagem vertical nesses casos, e o layout nunca precisa comprimir
    abaixo do mínimo de cada widget.

    Args:
        content: o QWidget cujo conteúdo (já com seu layout definido) deve
            se tornar rolável.
    """
    scroll = QScrollArea()
    scroll.setWidget(content)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    return scroll


def _sem_quebra_inicial(fragmento: str) -> str:
    """Remove só a quebra de linha introduzida pela abertura do bloco `\"\"\"`."""
    return fragmento[1:] if fragmento.startswith("\n") else fragmento


APP_STYLESHEET = (
    QSS_BASE
    + _sem_quebra_inicial(QSS_BUTTONS)
    + _sem_quebra_inicial(QSS_INPUTS)
    + _sem_quebra_inicial(QSS_LABELS)
    + _sem_quebra_inicial(QSS_WIDGETS)
)
