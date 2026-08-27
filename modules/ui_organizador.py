import os
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from modules.logger import UILogger
from modules.organizador import Organizador, ler_cabecalho_planilha
from modules.styles import scrollable


class OrganizadorWidget(QWidget):
    automatico_finished = pyqtSignal(bool, str)

    def __init__(self, parent_framework):
        super().__init__()
        self.parent_fw = parent_framework
        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        layout = QVBoxLayout(content)

        group_paths = QGroupBox("Pastas e Planilha")
        form_paths = QFormLayout()

        self.ent_propostas = QLineEdit()
        self.btn_propostas = QPushButton("Buscar Pasta")
        self.ent_pedidos = QLineEdit()
        self.btn_pedidos = QPushButton("Buscar Pasta")
        self.ent_destino = QLineEdit()
        self.btn_destino = QPushButton("Buscar Pasta")
        self.ent_planilha = QLineEdit()
        self.btn_planilha = QPushButton("Buscar Planilha")

        self.btn_propostas.clicked.connect(
            lambda: self._selecionar_pasta(self.ent_propostas, "Selecionar Pasta de Propostas")
        )
        self.btn_pedidos.clicked.connect(
            lambda: self._selecionar_pasta(self.ent_pedidos, "Selecionar Pasta de Pedidos")
        )
        self.btn_destino.clicked.connect(
            lambda: self._selecionar_pasta(self.ent_destino, "Selecionar Pasta de Destino")
        )
        self.btn_planilha.clicked.connect(self._selecionar_planilha)

        form_paths.addRow("Pasta Propostas:", self.add_layout(self.ent_propostas, self.btn_propostas))
        form_paths.addRow("Pasta Pedidos:", self.add_layout(self.ent_pedidos, self.btn_pedidos))
        form_paths.addRow("Pasta Destino:", self.add_layout(self.ent_destino, self.btn_destino))
        form_paths.addRow("Planilha (.xlsx/.csv):", self.add_layout(self.ent_planilha, self.btn_planilha))
        group_paths.setLayout(form_paths)
        layout.addWidget(group_paths)

        group_cols = QGroupBox("Configura\u00e7\u00e3o das Colunas (Opcional)")
        layout_cols = QHBoxLayout()
        layout_cols.addWidget(QLabel("Coluna RC:"))
        self.cbo_col_rc = self._criar_combo_coluna("Requisição")
        layout_cols.addWidget(self.cbo_col_rc)
        layout_cols.addWidget(QLabel("Coluna PO:"))
        self.cbo_col_po = self._criar_combo_coluna("Pedido")
        layout_cols.addWidget(self.cbo_col_po)
        layout_cols.addWidget(QLabel("Coluna Fornecedor:"))
        self.cbo_col_forn = self._criar_combo_coluna("Fornecedor")
        layout_cols.addWidget(self.cbo_col_forn)
        group_cols.setLayout(layout_cols)
        layout.addWidget(group_cols)

        self.btn_executar = QPushButton("Iniciar Organiza\u00e7\u00e3o")
        self.btn_executar.setObjectName("btnPrimary")
        self.btn_executar.clicked.connect(self.processar)
        layout.addWidget(self.btn_executar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        outer_layout.addWidget(scrollable(content))

    def _selecionar_pasta(self, entrada: QLineEdit, titulo: str) -> None:
        pasta = QFileDialog.getExistingDirectory(self, titulo)
        entrada.setText(os.path.normpath(pasta) if pasta else "")

    def _criar_combo_coluna(self, texto_padrao: str) -> QComboBox:
        """Combo editável: o usuário pode digitar livremente (como antes) ou
        escolher uma das colunas detectadas na planilha selecionada (ver
        _atualizar_colunas_detectadas)."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setEditText(texto_padrao)
        return combo

    def _selecionar_planilha(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar Planilha", filter="Planilhas (*.xlsx *.csv)")
        if not caminho:
            return
        self.ent_planilha.setText(caminho)
        self._atualizar_colunas_detectadas(caminho)

    def _atualizar_colunas_detectadas(self, caminho: str) -> None:
        """Lê o cabeçalho da planilha selecionada e preenche os combos de
        coluna com as opções reais encontradas - o texto digitado em cada
        combo só é substituído quando uma delas bate (sem distinção de
        maiúsculas) com o nome esperado (Requisição/Pedido/Fornecedor - os
        cabeçalhos gerados pela Aba 1, Extrator Inteligente); do contrário o
        combo so ganha as opções pra escolher, sem apagar o que já estava lá.
        """
        try:
            colunas = ler_cabecalho_planilha(Path(caminho))
        except Exception as e:
            self.log(f"⚠️ Não foi possível ler as colunas da planilha: {e}")
            return

        for combo, texto_padrao in (
            (self.cbo_col_rc, "Requisição"),
            (self.cbo_col_po, "Pedido"),
            (self.cbo_col_forn, "Fornecedor"),
        ):
            texto_atual = combo.currentText()
            combo.clear()
            combo.addItems(colunas)
            correspondencia = next(
                (coluna for coluna in colunas if coluna.strip().lower() == texto_padrao.lower()), None
            )
            combo.setEditText(correspondencia if correspondencia else texto_atual)

    def add_layout(self, edit, btn):
        btn_limpar = QPushButton("\u2716")
        btn_limpar.setToolTip("Limpar campo")
        btn_limpar.setFixedWidth(28)
        btn_limpar.setObjectName("btnClearField")
        # Item 23: Confirmação antes de limpar
        def confirmar_limpeza():
            if edit.text().strip():
                resposta = QMessageBox.question(
                    edit, "Confirmar Limpeza",
                    "Tem certeza que deseja limpar este campo?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if resposta == QMessageBox.StandardButton.Yes:
                    edit.clear()
            else:
                edit.clear()
        btn_limpar.clicked.connect(confirmar_limpeza)

        h_layout = QHBoxLayout()
        h_layout.addWidget(edit)
        h_layout.addWidget(btn)
        h_layout.addWidget(btn_limpar)
        h_layout.setContentsMargins(0, 0, 0, 0)
        widget = QWidget()
        widget.setLayout(h_layout)
        return widget

    def log(self, msg: str) -> None:
        UILogger.auto(self.log_area, msg)

    def check_prerequisites(self) -> tuple:
        """Verifica se a aba esta pronta para execucao automatica."""
        tem_propostas = bool(self.ent_propostas.text().strip())
        tem_pedidos = bool(self.ent_pedidos.text().strip())
        if not tem_propostas and not tem_pedidos:
            return False, "Informe pelo menos Pasta de Propostas ou Pasta de Pedidos"
        if not self.ent_destino.text().strip():
            return False, "Pasta de destino nao selecionada"
        if not self.ent_planilha.text().strip():
            return False, "Planilha nao selecionada"
        return True, "Pronto"

    def executar_automatico(self):
        """Executa organizacao automatica (modo cadeia)."""
        ok, msg = self.check_prerequisites()
        if not ok:
            self.automatico_finished.emit(False, f"Aba 5 pulada: {msg}")
            return
        self.processar(modo_automatico=True)

    def _strip_path(self, text: str) -> str:
        """Remove aspas e espacos extras de caminhos."""
        return text.strip().strip('"').strip("'")

    def _validar_pasta_existe(self, caminho: str, nome: str) -> bool:
        """Verifica se a pasta informada existe (se foi preenchida)."""
        if not caminho:
            return True
        return Path(caminho).is_dir()

    def processar(self, modo_automatico: bool = False) -> None:
        try:
            propostas = self._strip_path(self.ent_propostas.text())
            pedidos = self._strip_path(self.ent_pedidos.text())
            destino = self._strip_path(self.ent_destino.text())
            planilha = self._strip_path(self.ent_planilha.text())

            # Validar pastas antes de executar
            if propostas and not self._validar_pasta_existe(propostas, "Propostas"):
                raise ValueError(f"Pasta de Propostas nao encontrada: {propostas}")
            if pedidos and not self._validar_pasta_existe(pedidos, "Pedidos"):
                raise ValueError(f"Pasta de Pedidos nao encontrada: {pedidos}")

            organizador = Organizador(
                propostas=propostas,
                pedidos=pedidos,
                destino=destino,
                planilha=planilha,
                col_rc=self.cbo_col_rc.currentText().strip(),
                col_po=self.cbo_col_po.currentText().strip(),
                col_fornecedor=self.cbo_col_forn.currentText().strip(),
                logger=self.log
            )
            organizador.executar()

            if modo_automatico:
                self.automatico_finished.emit(True, "Aba 5 concluida: organizacao finalizada.")

        except Exception as e:
            erro_msg = f"\u274c Erro na organizacao: {str(e)}"
            self.log(erro_msg)
            if modo_automatico:
                self.automatico_finished.emit(False, erro_msg)
            else:
                QMessageBox.critical(self, "Erro", erro_msg)

