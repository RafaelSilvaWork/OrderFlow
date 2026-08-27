"""Bloqueia (ou desbloqueia) o acesso de uma pessoa específica ao app.

Uso:
    py -3 scripts/bloquear_usuario.py "username-do-windows"
    py -3 scripts/bloquear_usuario.py "username-do-windows" --desbloquear

O app é distribuído publicamente - qualquer pessoa pode baixar e usar o
instalador livremente. Este script cobre o caso reativo: revogar o acesso
de alguém específico depois do fato (ex: um ex-colaborador), sem afetar
mais ninguém. Só funciona pra marcas com um gist configurado (ver
ACCESS_GATE_GIST_ID em modules/branding.py) - a variante genérica não tem
gist próprio, então não há o que bloquear nela.

Para descobrir o username do Windows de uma pessoa, ver o evento
"Aplicativo iniciado" no Application Insights (modules/telemetry.py,
report_app_started) - cada abertura do app registra lá o usuário atual.

Requer o GitHub CLI (`gh`) instalado e autenticado (`gh auth status`) com a
conta dona do gist de controle de acesso, e a variável de ambiente
CFW_ACCESS_GATE_GIST_ID definida com o ID desse gist (o mesmo valor
configurado como secret ACCESS_GATE_GIST_ID no repositório, ver
modules/branding.py e a docstring de modules/access_gate.py) - nunca
hardcoded aqui, pelo mesmo motivo do módulo. Roda só na máquina de quem
administra o acesso - não é distribuído com o instalador do app (fica fora
de modules/, então o PyInstaller nunca empacota isto).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GIST_ID = os.environ.get("CFW_ACCESS_GATE_GIST_ID", "").strip()
GIST_FILE_NAME = "access.json"


def _run_gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Erro ao rodar 'gh {' '.join(args)}':\n{result.stderr.strip()}")
    return result.stdout


def _fetch_gist_content() -> dict:
    raw = _run_gh("gist", "view", GIST_ID, "-f", GIST_FILE_NAME)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"O conteúdo atual do gist não é um JSON válido: {exc}")


def _write_gist_content(content: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(content, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    try:
        _run_gh("gist", "edit", GIST_ID, "--filename", GIST_FILE_NAME, str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    if not GIST_ID:
        sys.exit(
            "Defina a variável de ambiente CFW_ACCESS_GATE_GIST_ID com o ID do gist "
            "de controle de acesso antes de rodar este script (ver docstring do módulo)."
        )

    args = sys.argv[1:]
    desbloquear = "--desbloquear" in args
    args = [a for a in args if a != "--desbloquear"]

    if len(args) != 1 or not args[0].strip():
        sys.exit(
            'Uso: py -3 scripts/bloquear_usuario.py "username-do-windows" [--desbloquear]'
        )
    username = args[0].strip()

    content = _fetch_gist_content()
    blocked_users = content.setdefault("blocked_users", [])
    if not isinstance(blocked_users, list):
        sys.exit(
            "O campo 'blocked_users' do gist está num formato inesperado "
            "(não é uma lista) - corrija manualmente pelo navegador antes de continuar."
        )

    ja_bloqueado = any(isinstance(u, str) and u.strip().lower() == username.lower() for u in blocked_users)

    if desbloquear:
        if not ja_bloqueado:
            print(f'"{username}" já não está na lista de bloqueados. Nada a fazer.')
            return
        content["blocked_users"] = [
            u for u in blocked_users if not (isinstance(u, str) and u.strip().lower() == username.lower())
        ]
        _write_gist_content(content)
        print(f'"{username}" foi removido da lista de bloqueados - acesso liberado novamente.')
    else:
        if ja_bloqueado:
            print(f'"{username}" já está na lista de bloqueados. Nada a fazer.')
            return
        blocked_users.append(username)
        _write_gist_content(content)
        print(f'"{username}" foi adicionado à lista de bloqueados.')
        print("O acesso dela para na próxima vez que o app abrir com internet.")


if __name__ == "__main__":
    main()
