"""Controle de acesso do framework por lista de bloqueio.

O app é distribuído publicamente - qualquer pessoa no mundo pode baixar o
instalador e usar livremente, sem precisar pedir nada a ninguém. Este módulo
existe só para o caso reativo: revogar o acesso de alguém específico (ex: um
ex-colaborador da empresa) depois do fato, sem afetar mais ninguém.

A cada abertura, o app consulta um gist secreto no GitHub (só leitura -
nenhuma credencial de escrita é distribuída com o app) para saber se:
  - o acesso está desligado globalmente ("access_enabled": false), ou
  - o usuário do Windows atual está na lista "blocked_users"

Fail-open por design: qualquer falha de rede, timeout ou resposta
inesperada libera o uso normalmente - o framework já depende de internet
para falar com o Coupa, então quem está genuinamente offline não consegue
usar o app de qualquer forma; a checagem serve só para permitir revogar
acesso remotamente quando a conexão está disponível.

O gist usado é definido por ACCESS_GATE_GIST_ID em modules/branding.py, por
marca - vazio na variante genérica (nenhum gist próprio configurado ainda
significa ninguém bloqueado, sem nem fazer a chamada de rede). Pra ativar
esse recurso na sua própria marca/fork, crie um gist secreto com um arquivo
"access.json" (formato: {"access_enabled": true, "blocked_users": []}) e
aponte ACCESS_GATE_GIST_ID pra ele.

Para bloquear/desbloquear alguém (marca com gist configurado): usar
scripts/bloquear_usuario.py (ou o .bat) com o USERNAME do Windows dela, ou
editar o gist manualmente. Para bloquear todo mundo de uma vez:
"access_enabled": false no gist.

Para descobrir o USERNAME do Windows de alguém, ver o evento "Aplicativo
iniciado" reportado no Application Insights (modules/telemetry.py,
report_app_started) - cada abertura do app registra lá o usuário atual.
"""

import json
import logging
import os

import requests

from modules.branding import ACCESS_GATE_GIST_ID, APP_DISPLAY_NAME

logger = logging.getLogger(__name__)

GIST_ID = ACCESS_GATE_GIST_ID
GIST_FILE_NAME = "access.json"
_REQUEST_TIMEOUT_SECONDS = 5
_DEFAULT_BLOCK_MESSAGE = f"Acesso ao {APP_DISPLAY_NAME} foi revogado."


def current_username() -> str:
    """Nome de usuário do Windows da sessão atual (vazio se indisponível)."""
    return os.environ.get("USERNAME", "").strip()


def check_access() -> tuple[bool, str]:
    """Retorna (acesso_liberado, mensagem_de_bloqueio).

    Sempre retorna (True, "") quando não é possível determinar o estado
    remoto (ver docstring do módulo sobre fail-open), quando
    "access_enabled" não for um booleano explícito, quando o usuário
    atual não estiver na lista "blocked_users", ou quando nenhum gist
    estiver configurado para esta marca (GIST_ID vazio - ver
    ACCESS_GATE_GIST_ID em modules/branding.py) - nesse último caso nem
    chega a fazer a chamada de rede.
    """
    if not GIST_ID:
        return True, ""

    try:
        response = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            timeout=_REQUEST_TIMEOUT_SECONDS,
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        data = response.json()
        file_entry = (data.get("files") or {}).get(GIST_FILE_NAME) or {}
        content = json.loads(file_entry.get("content") or "{}")

        access_enabled = content.get("access_enabled", True)
        if isinstance(access_enabled, bool) and not access_enabled:
            message = str(content.get("message") or "").strip() or _DEFAULT_BLOCK_MESSAGE
            return False, message

        blocked_users = content.get("blocked_users") or []
        blocked_normalized = {
            entry.strip().lower() for entry in blocked_users if isinstance(entry, str) and entry.strip()
        }
        username = current_username()
        if username and username.lower() in blocked_normalized:
            message = str(content.get("message") or "").strip() or _DEFAULT_BLOCK_MESSAGE
            return False, message

        return True, ""
    except Exception as exc:
        logger.warning("Checagem de acesso remoto falhou, liberando por padrão (fail-open): %s", exc)
        return True, ""
