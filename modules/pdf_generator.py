import contextlib
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from modules import module_checkpoint
from modules.config import (
    ESPERA_ENTRE_TENTATIVAS,
    MARGENS_IMPRESSAO,
    MAX_TENTATIVAS,
    PERFIL_EDGE_DOWNLOAD,
    TEXTOS_SEM_DOCUMENTO,
    get_url_base_impressao_pdf,
    get_url_teste_login,
    resolve_edge_executable,
)
from modules.playwright_pool import PlaywrightContextSyncManager


class PdfGeneratorWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(
        self,
        pedidos: list[str],
        pasta_saida: str,
        requisicoes_por_pedido: dict[str, list[str]] | None = None,
        pedidos_originais: list[str] | None = None,
        resultados_anteriores: list[dict] | None = None,
    ):
        super().__init__()
        self.pedidos = pedidos
        self.pasta_saida = Path(pasta_saida)
        self.requisicoes_por_pedido = requisicoes_por_pedido or {}
        self.cancelado = False
        # pedidos_originais/resultados_anteriores só vêm preenchidos numa
        # RETOMADA de checkpoint (ver modules/module_checkpoint.py e
        # _oferecer_retomada_checkpoint em ui_pdf_generator.py) - "pedidos"
        # já é só o que falta gerar; o checkpoint continua precisando do
        # conjunto original completo e do que já tinha sido gerado antes do
        # crash/cancelamento, pra combinar no relatório e no resultado final.
        self.pedidos_originais = pedidos_originais if pedidos_originais is not None else pedidos
        resultados_anteriores = resultados_anteriores or []
        self._resultados_anteriores_dict = {
            item["pedido"]: {
                "status": "Sucesso" if item.get("status") == "sucesso" else "Erro",
                "detalhe": item.get("detalhe", ""),
            }
            for item in resultados_anteriores
        }
        self._contagem_anterior = {
            "sucesso": sum(1 for item in resultados_anteriores if item.get("status") == "sucesso"),
            "sem_documento": sum(1 for item in resultados_anteriores if item.get("status") == "sem_documento"),
            "falha": sum(1 for item in resultados_anteriores if item.get("status") == "falha"),
        }
        # Acumulador do checkpoint - começa com o que já veio de antes e
        # cresce a cada pedido concluído nesta execução (ver run()).
        self._resultados_checkpoint: list[dict] = list(resultados_anteriores)

    def gerar_relatorio(self, resultados: dict[str, dict[str, str]]) -> Path:
        linhas = []
        for pedido in self.pedidos_originais:
            resultado = resultados.get(pedido, {"status": "Cancelado", "detalhe": "Não processado"})
            requisicoes = self.requisicoes_por_pedido.get(pedido) or ["Não informada"]
            for requisicao in requisicoes:
                linhas.append(
                    {
                        "Número da Requisição": requisicao,
                        "Número do Pedido": pedido,
                        "Status": resultado["status"],
                        "Detalhe": resultado["detalhe"],
                        "Arquivo PDF": f"{pedido}.pdf" if resultado["status"] == "Sucesso" else "",
                    }
                )

        caminho = self.pasta_saida / f"Relatorio_Geracao_PDF_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
            pd.DataFrame(linhas).to_excel(writer, index=False, sheet_name="Resultado PDFs")
            planilha = writer.sheets["Resultado PDFs"]
            planilha.freeze_panes = "A2"
            for coluna in planilha.columns:
                letra = coluna[0].column_letter
                planilha.column_dimensions[letra].width = min(
                    max(len(str(c.value or "")) for c in coluna) + 2, 60
                )
        return caminho

    def run(self):
        self.log_signal.emit(">>> Inicializando o ambiente do Edge para PDF...")
        self.pasta_saida.mkdir(parents=True, exist_ok=True)

        sucesso, sem_documento, falha = [], [], []
        resultados = dict(self._resultados_anteriores_dict)
        total = len(self.pedidos)

        # Aponta para o mesmo perfil de download para reaproveitar a sessão/cookies logados
        user_data_dir = str(PERFIL_EDGE_DOWNLOAD)
        caminho_edge = resolve_edge_executable()

        if not caminho_edge or not Path(caminho_edge).exists():
            self.log_signal.emit("❌ ERRO CRÍTICO: Caminho do Microsoft Edge não encontrado ou inválido.")
            self.finished_signal.emit("Microsoft Edge não encontrado para geração de PDF.")
            return

        try:
            # Utiliza o gerenciador síncrono blindado do pool
            with PlaywrightContextSyncManager(
                user_data_dir=user_data_dir
            ) as context:
                pages = context.pages
                page = pages[0] if pages else context.new_page()
                page.set_default_timeout(45000)

                with contextlib.suppress(Exception):
                    # timeout esperado se a página de teste já estiver carregada
                    page.goto(get_url_teste_login(), wait_until="domcontentloaded")

                with contextlib.suppress(Exception):
                    # rede pode nunca ficar ociosa; segue com o que já carregou
                    page.wait_for_load_state("networkidle", timeout=8000)

                deslogado = (
                    "login" in page.url.lower()
                    or "sso" in page.url.lower()
                    or page.query_selector("input[type='password']") is not None
                )

                if not deslogado:
                    self.log_signal.emit("✅ Sessão compartilhada ativa detectada automaticamente!")
                else:
                    self.log_signal.emit("⚠️ Login necessário! Conclua o login corporativo na janela do Edge...")
                    page.wait_for_function(
                        """() => {
                            const url = location.href.toLowerCase();
                            return !url.includes('login')
                                && !url.includes('sso')
                                && !document.querySelector("input[type='password']");
                        }""",
                        timeout=300000,
                    )
                    self.log_signal.emit("✅ Autenticado com sucesso no portal Coupa!")

                self.log_signal.emit(f">>> Processando lote de {total} pedido(s)...")

                for i, ped in enumerate(self.pedidos, 1):
                    if self.cancelado:
                        break

                    url_print = get_url_base_impressao_pdf(ped)
                    self.log_signal.emit(f"📄 Abrindo leiaute de impressão para o Pedido #{ped}...")

                    status_checkpoint, detalhe_checkpoint = "falha", ""
                    try:
                        page.goto(url_print, wait_until="domcontentloaded", timeout=45000)

                        with contextlib.suppress(Exception):
                            # timeout esperado; a checagem de "documento pronto" segue abaixo
                            page.wait_for_load_state("load", timeout=5000)

                        doc_pronto = False
                        for tentativa in range(1, MAX_TENTATIVAS + 1):
                            time.sleep(0.5)

                            conteudo = page.content().lower()
                            existe_erro = any(texto_err.lower() in conteudo for texto_err in TEXTOS_SEM_DOCUMENTO)

                            if not existe_erro:
                                doc_pronto = True
                                break

                            if tentativa < MAX_TENTATIVAS:
                                self.log_signal.emit(
                                    f"⏳ Documento do Pedido #{ped} ainda em processamento. "
                                    f"Tentando recarregar em {ESPERA_ENTRE_TENTATIVAS}s..."
                                )
                                time.sleep(ESPERA_ENTRE_TENTATIVAS)
                                page.reload(wait_until="domcontentloaded")

                        if doc_pronto:
                            page.emulate_media(media="print")
                            destino_pdf = self.pasta_saida / f"{ped}.pdf"
                            page.pdf(
                                path=str(destino_pdf),
                                format="A4",
                                print_background=True,
                                margin=MARGENS_IMPRESSAO,
                            )
                            self.log_signal.emit(f"✅ Sucesso: Pedido {ped} compilado em {destino_pdf.name}")
                            sucesso.append(ped)
                            resultados[ped] = {
                                "status": "Sucesso",
                                "detalhe": "PDF gerado com sucesso",
                            }
                            status_checkpoint, detalhe_checkpoint = "sucesso", "PDF gerado com sucesso"
                        else:
                            self.log_signal.emit(f"⚠️ Pulado: Pedido {ped} ainda está em processamento interno.")
                            sem_documento.append(ped)
                            resultados[ped] = {
                                "status": "Erro",
                                "detalhe": "Documento ainda em processamento interno",
                            }
                            status_checkpoint = "sem_documento"
                            detalhe_checkpoint = "Documento ainda em processamento interno"

                    except Exception as e:
                        self.log_signal.emit(f"❌ Falha no processamento do Pedido #{ped}: {str(e)}")
                        falha.append(ped)
                        resultados[ped] = {"status": "Erro", "detalhe": str(e)}
                        status_checkpoint, detalhe_checkpoint = "falha", str(e)

                    finally:
                        # Roda ao fim de CADA pedido, independente do
                        # resultado - ver modules/module_checkpoint.py. Sem
                        # isso, um crash no meio de um lote longo perdia
                        # tudo o que já tinha sido gerado até ali.
                        self._resultados_checkpoint.append(
                            {"pedido": ped, "status": status_checkpoint, "detalhe": detalhe_checkpoint}
                        )
                        module_checkpoint.save(
                            "pdf",
                            self.pedidos_originais,
                            {"requisicoes_por_pedido": self.requisicoes_por_pedido},
                            self._resultados_checkpoint,
                        )

                    self.progress_signal.emit(int((i / total) * 100))
                else:
                    # "else" do for: só roda se o loop terminou sem "break"
                    # (cancelamento) - passou por todos os pedidos pendentes,
                    # o checkpoint cumpriu seu papel.
                    module_checkpoint.clear("pdf")

            relatorio = self.gerar_relatorio(resultados)
            self.log_signal.emit(f"📊 Relatório salvo em: {relatorio}")
            total_sucesso = len(sucesso) + self._contagem_anterior["sucesso"]
            total_sem_documento = len(sem_documento) + self._contagem_anterior["sem_documento"]
            total_falha = len(falha) + self._contagem_anterior["falha"]
            resumo = (
                f"Processo concluído: {total_sucesso} Sucesso(s) | {total_sem_documento} Sem Doc | "
                f"{total_falha} Falha(s). Relatório: {relatorio.name}"
            )
            self.finished_signal.emit(resumo)

        except Exception as e:
            self.log_signal.emit(f"❌ ERRO CRÍTICO na Thread do Gerador: {str(e)}")
            for pedido in self.pedidos:
                resultados.setdefault(pedido, {"status": "Erro", "detalhe": f"Falha interna: {str(e)}"})
            try:
                relatorio = self.gerar_relatorio(resultados)
                self.log_signal.emit(f"📊 Relatório salvo em: {relatorio}")
                self.finished_signal.emit(
                    f"Ocorreu uma falha interna na execução do Edge. Relatório: {relatorio.name}"
                )
            except Exception as erro_relatorio:
                self.log_signal.emit(f"❌ Não foi possível gerar o relatório: {erro_relatorio}")
                self.finished_signal.emit(
                    "Ocorreu uma falha interna na execução do Edge."
                )

    def cancelar(self):
        self.cancelado = True
