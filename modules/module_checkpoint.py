"""Checkpoint de execução por módulo, para sobreviver a um travamento/crash.

Se o app travar no meio de uma execução longa (Extrator, Baixador de
Orçamentos ou Gerador de PDF de Pedidos) e precisar ser fechado à força,
sem isso o usuário perderia todo o progresso e teria que refazer tudo do
zero. Cada módulo grava seu progresso incrementalmente (ver save, chamado
a cada item concluído) e oferece retomar de onde parou na próxima vez que
o usuário for iniciar aquele módulo.

Um arquivo POR MÓDULO (não um só compartilhado como modules/
execution_history.py) - cada aba roda seu worker numa QThread própria, e
usar arquivos separados evita qualquer risco de uma escrever por cima do
checkpoint da outra se duas execuções acontecerem em paralelo.

Módulos que NÃO usam isto, de propósito:
- Disparo de E-mails: retomar arriscaria reenviar um e-mail que já saiu.
- Renomeador: já é naturalmente seguro contra crash - "Analisar" sempre
  reflete o estado ATUAL da pasta, então um arquivo já renomeado numa
  execução anterior simplesmente não aparece mais como pendente.
"""

import json
import logging

from modules.config import USER_DATA_DIR

logger = logging.getLogger(__name__)


def _checkpoint_path(module_key: str):
    return USER_DATA_DIR / f"checkpoint_{module_key}.json"


def save(module_key: str, itens_originais: list, extra: dict, resultados: list) -> None:
    """Grava o progresso atual do módulo. Best-effort: chamado a cada item
    concluído, então uma falha aqui não deve interromper a execução - só
    fica sem esse checkpoint específico."""
    path = _checkpoint_path(module_key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "itens_originais": itens_originais,
                    "extra": extra,
                    "resultados": resultados,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        logger.warning("Falha ao gravar checkpoint do módulo '%s'.", module_key)


def load(module_key: str) -> dict | None:
    """Retorna o checkpoint salvo do módulo, ou None se não houver um (ou
    estiver corrompido - tratado como inexistente, nunca quebra o início
    de uma execução nova)."""
    try:
        return json.loads(_checkpoint_path(module_key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def clear(module_key: str) -> None:
    try:
        _checkpoint_path(module_key).unlink(missing_ok=True)
    except OSError:
        logger.warning("Falha ao remover checkpoint do módulo '%s'.", module_key)


def pending_items(checkpoint: dict, chave: str) -> list:
    """Itens do checkpoint que ainda não foram processados, na mesma ordem
    original. `chave` é o campo usado em cada dict de "resultados" para
    identificar a qual item original ele corresponde (ex: "requisicao",
    "pedido")."""
    processados = {item.get(chave) for item in checkpoint.get("resultados", [])}
    return [i for i in checkpoint.get("itens_originais", []) if i not in processados]
