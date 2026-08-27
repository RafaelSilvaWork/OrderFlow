"""Configuração de marca (branding) do framework.

Permite compilar DUAS variantes a partir do MESMO código-fonte:
  - "hapvida" (padrão): a versão interna, com a marca do Hapvida.
  - "generic": versão de código aberto ("OrderFlow"), sem nenhuma marca de
    terceiro (nem Hapvida, nem Coupa) - pensada pra ser publicada num
    repositório público.

A variante ativa é escolhida pela env var CFW_BRANDING, definida em tempo de
build (CI) ou execução (dev). Nada disso afeta a lógica de automação em si -
só nome de exibição, ícone, splash e o repositório do GitHub usado pelo
auto-update (ver modules/updater.py).
"""

import os

BRANDING = os.environ.get("CFW_BRANDING", "hapvida").strip().lower()
IS_GENERIC = BRANDING == "generic"

APP_DISPLAY_NAME = "OrderFlow" if IS_GENERIC else "Coupa Framework"

# Nome da pasta de dados locais (%APPDATA%/%LOCALAPPDATA%) - perfil do Edge,
# logs, cache do updater, histórico do renomeador etc. Isolado por marca de
# propósito: instalar as duas variantes na mesma máquina (ex: teste local)
# nunca deve fazer uma compartilhar perfil/config com a outra.
APP_DATA_DIR_NAME = "OrderFlow" if IS_GENERIC else "CoupaFramework"

_ASSETS_DIR = "assets/branding/generic" if IS_GENERIC else "assets/branding/hapvida"
ICON_PATH = f"{_ASSETS_DIR}/icon.ico"
LOGO_PECAS_DIR = f"{_ASSETS_DIR}/logo_pecas"

# Ordem das peças da splash animada (ver modules/splash_screen.py) - a marca
# genérica tem só o ícone (peça única, balançando sozinha); a do Hapvida
# soletra o nome completo, letra por letra, ao lado do ícone.
LOGO_PECAS_ORDEM: tuple[str, ...] = (
    ("icone",) if IS_GENERIC else ("icone", "h", "a1", "p", "v", "i", "d", "a2")
)

# Repositório do GitHub consultado pelo auto-update (ver GITHUB_REPO em
# modules/updater.py) - cada variante aponta pro seu próprio repositório,
# então uma nunca tenta se atualizar com a release da outra.
GITHUB_REPO = "RafaelSilvaWork/OrderFlow" if IS_GENERIC else "RafaelSilvaWork/Coupa-Framework"

# Gist usado pelo controle de acesso remoto (ver modules/access_gate.py).
# Fica vazio aqui de propósito, inclusive na variante hapvida - o valor real
# é injetado SÓ em tempo de build (mesmo mecanismo do
# APPINSIGHTS_CONNECTION_STRING em modules/config.py: um step do workflow de
# release reescreve este literal com o secret ACCESS_GATE_GIST_ID do repo
# privado antes de compilar - ver ".github/workflows/release.yml"). Nunca
# hardcode o valor real aqui: esse gist pode conter usernames reais de quem
# foi bloqueado, e este arquivo é compartilhado com a variante pública (open
# source) - um literal no código-fonte ficaria legível por qualquer um,
# mesmo num branch/valor que essa variante nunca usa em runtime. Sem o
# secret configurado (build local, ou o repo público, que nunca tem esse
# secret), o controle de acesso fica vazio/desligado (fail-open).
ACCESS_GATE_GIST_ID = ""
