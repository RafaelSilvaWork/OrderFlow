from datetime import datetime

from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from modules.execution_history import load_history
from modules.feature_selection import MODULE_DEFINITIONS
from modules.styles import aplicar_titlebar_escura, scrollable, set_status


def _format_timestamp(iso_text: str) -> str:
    try:
        return datetime.fromisoformat(iso_text).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso_text


class ExecutionHistoryDialog(QDialog):
    """Mostra as últimas execuções de cada módulo (ver modules/execution_history.py).

    "Gerenciar Perfis" fica de fora - é configuração, não uma execução com
    resultado pra registrar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Histórico de execuções")
        aplicar_titlebar_escura(self)
        self.resize(520, 560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        title = QLabel("Últimas execuções por módulo")
        title.setObjectName("titleLabel")
        outer.addWidget(title)

        subtitle = QLabel(
            "Só um resumo de cada execução - os dados completos continuam nos "
            "logs e exports de cada aba."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("lockedModuleDesc")
        outer.addWidget(subtitle)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        for module_key, label in MODULE_DEFINITIONS:
            if module_key == "perfis":
                continue
            layout.addWidget(self._build_module_section(module_key, label))
        layout.addStretch()

        outer.addWidget(scrollable(container), 1)

    def _build_module_section(self, module_key: str, label: str) -> QFrame:
        section = QFrame()
        section.setObjectName("lockedModuleCard")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(16, 12, 16, 12)
        section_layout.setSpacing(6)

        lbl_title = QLabel(label)
        lbl_title.setObjectName("lockedModuleTitle")
        lbl_title.setStyleSheet("font-size: 15px;")
        section_layout.addWidget(lbl_title)

        entradas = load_history(module_key)
        if not entradas:
            lbl_empty = QLabel("Nenhuma execução registrada ainda.")
            set_status(lbl_empty, "muted")
            section_layout.addWidget(lbl_empty)
            return section

        for entrada in entradas:
            row = QHBoxLayout()

            lbl_time = QLabel(_format_timestamp(entrada.get("timestamp", "")))
            lbl_time.setObjectName("lockedModuleDesc")
            lbl_time.setMinimumWidth(130)
            row.addWidget(lbl_time)

            icone = "✅" if entrada.get("success") else "❌"
            lbl_summary = QLabel(f"{icone} {entrada.get('summary', '')}")
            lbl_summary.setWordWrap(True)
            row.addWidget(lbl_summary, 1)

            section_layout.addLayout(row)

        return section
