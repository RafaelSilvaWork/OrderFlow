"""Módulo do framework de automação Coupa.

Exporta todas as classes públicas para imports simplificados.
Use: from modules import CoupaExtractorWidget, OrcamentoDownloaderWidget, ...

Os widgets/workers abaixo são carregados sob demanda (PEP 562, ver
__getattr__ no fim do arquivo), não no import do pacote - cada um arrasta
uma biblioteca pesada (Playwright, pandas, PyMuPDF, docx, pptx), e
"import modules" acontece só de importar QUALQUER submódulo (ex:
modules.access_gate), então carregar tudo de cara aqui fazia o app demorar
vários segundos pra mostrar até a primeira tela (ver main.py,
_carregar_modulos_pesados e a splash screen). Acessar qualquer um desses
nomes (`from modules import CoupaExtractorWidget` ou `modules.CoupaExtractorWidget`)
importa só aquele, na hora, e fica em cache pros próximos acessos.
"""

import importlib
import logging
import os
import traceback
from pathlib import Path

from modules.branding import APP_DATA_DIR_NAME

# Registro dos erros reais de import, por nome de atributo (widget/worker).
# main.py consulta isso para saber POR QUE um módulo veio None, em vez de
# simplesmente tentar instanciar None e crashar.
IMPORT_ERRORS: dict[str, str] = {}


def _get_logger() -> logging.Logger:
    logger = logging.getLogger(f"{APP_DATA_DIR_NAME}.imports")
    if logger.handlers:
        return logger
    try:
        log_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_DATA_DIR_NAME / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "import_errors.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
    except Exception:
        pass  # se nem o log conseguir ser criado, seguimos sem travar o app
    return logger


def _safe_import(attr_name: str, module_name: str):
    try:
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)
    except ModuleNotFoundError as exc:
        if getattr(exc, "name", None) == module_name:
            # O arquivo do próprio módulo não existe neste PC (instalação seletiva
            # removeu o módulo, ou ele nunca foi baixado) - não é um bug, é o
            # estado esperado de "módulo não instalado". Não registra em
            # IMPORT_ERRORS para a tela bloqueada mostrar a mensagem amigável de
            # "não instalado" em vez de um traceback de erro interno.
            return None
        err_text = traceback.format_exc()
        IMPORT_ERRORS[attr_name] = err_text
        _get_logger().error("Falha ao importar '%s' de '%s':\n%s", attr_name, module_name, err_text)
        return None
    except Exception:
        err_text = traceback.format_exc()
        IMPORT_ERRORS[attr_name] = err_text
        _get_logger().error("Falha ao importar '%s' de '%s':\n%s", attr_name, module_name, err_text)
        return None


# Mapa nome_publico -> (nome_do_atributo_na_origem, modulo_de_origem), usado
# por __getattr__ pra importar cada um só quando for realmente acessado.
_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    # Widgets de Interface
    "CoupaExtractorWidget": ("CoupaExtractorWidget", "modules.ui_coupa"),
    "OrcamentoDownloaderWidget": ("OrcamentoDownloaderWidget", "modules.ui_downloader"),
    "PedidoPdfGeneratorWidget": ("PedidoPdfGeneratorWidget", "modules.ui_pdf_generator"),
    "RenomeadorWidget": ("RenomeadorWidget", "modules.ui_renomeador"),
    "OrganizadorWidget": ("OrganizadorWidget", "modules.ui_organizador"),
    "EmailSenderWidget": ("EmailSenderWidget", "modules.ui_email_sender"),
    "ProfileManagerWidget": ("ProfileManagerWidget", "modules.ui_profile_manager"),
    # Workers
    "CoupaScraper": ("CoupaScraper", "modules.coupa_scraper"),
    "AutomationWorker": ("AutomationWorker", "modules.coupa_scraper"),
    "DownloadScraper": ("DownloadScraper", "modules.download_scraper"),
    "DownloadWorker": ("DownloadWorker", "modules.download_scraper"),
    "EmailWorker": ("EmailWorker", "modules.email_sender"),
    "PdfGeneratorWorker": ("PdfGeneratorWorker", "modules.pdf_generator"),
    # Lógica de Negócio
    "Organizador": ("Organizador", "modules.organizador"),
    "ProfileManager": ("ProfileManager", "modules.config"),
    # Fluxo Automático
    "AutomaticFlowRunner": ("AutomaticFlowRunner", "modules.fluxo_orquestrador"),
    "ModoAutomatico": ("ModoAutomatico", "modules.fluxo_orquestrador"),
}


def __getattr__(name: str):
    """PEP 562: resolve os nomes de _LAZY_ATTRS sob demanda, na primeira vez
    que forem acessados - e só nessa vez, já que o resultado é gravado direto
    no namespace do pacote (globals()), então acessos seguintes nem chamam
    esta função de novo."""
    par = _LAZY_ATTRS.get(name)
    if par is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    attr_name, module_name = par
    valor = _safe_import(attr_name, module_name)
    globals()[name] = valor
    return valor


__all__ = [
    # Widgets
    "CoupaExtractorWidget",
    "OrcamentoDownloaderWidget",
    "PedidoPdfGeneratorWidget",
    "RenomeadorWidget",
    "OrganizadorWidget",
    "EmailSenderWidget",
    "ProfileManagerWidget",
    # Workers
    "CoupaScraper",
    "AutomationWorker",
    "DownloadScraper",
    "DownloadWorker",
    "EmailWorker",
    "PdfGeneratorWorker",
    # Lógica
    "Organizador",
    "ProfileManager",
    # Fluxo
    "AutomaticFlowRunner",
    "ModoAutomatico",
]
