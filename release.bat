@echo off
title Release - OrderFlow
setlocal EnableDelayedExpansion

echo ============================================================
echo  OrderFlow - Publicar Nova Versao
echo ============================================================
echo.
echo O build do instalador e a publicacao no GitHub agora sao feitos
echo automaticamente pelo workflow .github\workflows\release.yml assim
echo que a tag for enviada. Este script so cuida do versionamento.
echo.

:: Verifica gh CLI
gh --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] GitHub CLI nao encontrado.
    echo Instale em: https://cli.github.com
    pause
    exit /b 1
)

:: Verifica autenticacao gh
gh auth status > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Nao autenticado no GitHub CLI. Execute: gh auth login
    pause
    exit /b 1
)

:: Pede a nova versao
set /p VERSION="Digite a nova versao (ex: 1.1.1): "
if "%VERSION%"=="" (
    echo [ERRO] Versao nao informada.
    pause
    exit /b 1
)

:: Verifica se essa versao ja existe (tag local ou release no GitHub) ANTES de
:: bumpar versao e commitar - falha rapido em vez de so quando o CI publicar.
echo.
echo Verificando se a versao v%VERSION% ja existe...

git rev-parse "v%VERSION%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [ERRO] A tag "v%VERSION%" ja existe localmente no Git.
    echo Escolha outro numero de versao ou apague a tag antiga com: git tag -d v%VERSION%
    pause
    exit /b 1
)

gh release view "v%VERSION%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [ERRO] Ja existe uma release "v%VERSION%" publicada no GitHub.
    echo Escolha outro numero de versao.
    pause
    exit /b 1
)
echo       OK, versao disponivel.

echo.
echo [1/2] Atualizando versao para %VERSION%...

:: Atualiza CURRENT_VERSION no updater.py
powershell -Command "(Get-Content modules\updater.py) -replace 'CURRENT_VERSION = \".*\"', 'CURRENT_VERSION = \"%VERSION%\"' | Set-Content modules\updater.py"

:: Atualiza a versao no installer.iss - so precisa tocar em MyAppVersion, ja
:: que AppVersion/OutputBaseFilename/UninstallDisplayName/VersionInfoVersion
:: sao todos derivados dele via preprocessador do Inno Setup (ver defines no
:: topo do installer.iss e modules/branding.py para o resto da marca).
powershell -Command "(Get-Content installer.iss) -replace '#define MyAppVersion \".*\"', '#define MyAppVersion \"%VERSION%\"' | Set-Content installer.iss"

echo       OK

echo.
echo [2/2] Commit e tag no Git...
git add modules\updater.py installer.iss
git commit -m "chore: bump version to v%VERSION%"
git tag "v%VERSION%"
git push
git push origin "v%VERSION%"
if %errorlevel% neq 0 (
    echo [ERRO] Falha no push. Verifique sua conexao e permissoes.
    pause
    exit /b 1
)
echo       OK

echo.
echo ============================================================
echo  Tag v%VERSION% enviada! O GitHub Actions vai buildar e publicar
echo  a release sozinho em poucos minutos.
echo  Acompanhe em: https://github.com/RafaelSilvaWork/OrderFlow/actions
echo ============================================================
pause
