"""Histórico das últimas execuções de cada módulo (aba).

Guarda só um resumo curto por execução (não os dados completos - esses já
ficam nos logs e exports de cada aba), pra consulta rápida sem precisar
vasculhar log antigo. Ver ExecutionHistoryDialog (modules/ui_execution_history.py)
pra tela que lê esse arquivo.
"""

import json
import logging
from datetime import datetime

from filelock import FileLock, Timeout

from modules.config import HISTORICO_EXECUCOES

logger = logging.getLogger(__name__)

MAX_ENTRIES_PER_MODULE = 5


def _read_all() -> dict:
    try:
        return json.loads(HISTORICO_EXECUCOES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def record_execution(module_key: str, success: bool, summary: str) -> None:
    """Registra uma execução concluída do módulo, mantendo só as últimas
    MAX_ENTRIES_PER_MODULE (mais recente primeiro).

    Best-effort de propósito: chamado sempre no fim de uma execução (manual
    ou via fluxo automático), então uma falha aqui (disco cheio, lock
    travado por outro processo etc.) nunca deve impedir o módulo de
    terminar normalmente - só fica sem esse registro específico.
    """
    lock_path = HISTORICO_EXECUCOES.with_suffix(HISTORICO_EXECUCOES.suffix + ".lock")
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "success": success,
        "summary": summary,
    }
    try:
        HISTORICO_EXECUCOES.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(lock_path, timeout=5):
            dados = _read_all()
            entradas = dados.get(module_key, [])
            entradas.insert(0, entry)
            dados[module_key] = entradas[:MAX_ENTRIES_PER_MODULE]
            HISTORICO_EXECUCOES.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Timeout:
        logger.warning("Não foi possível travar o arquivo de histórico de execuções: %s", lock_path)
    except OSError:
        logger.warning("Falha ao gravar histórico de execuções do módulo '%s'", module_key)


def load_history(module_key: str) -> list[dict]:
    return _read_all().get(module_key, [])
