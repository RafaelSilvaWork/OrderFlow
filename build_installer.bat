@echo off
title Build - OrderFlow
setlocal EnableDelayedExpansion

echo ============================================================
echo  OrderFlow - Build do Instalador (4 etapas)
echo ============================================================
echo.

py --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale o Python 3.10+ e tente novamente.
    pause
    exit /b 1
)

echo [1/4] Instalando PyInstaller...
py -m pip install --upgrade pyinstaller > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar PyInstaller.
    pause
    exit /b 1
)
echo       OK

echo [2/4] Instalando dependencias do projeto...
py -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias. Veja os erros acima.
    pause
    exit /b 1
)
echo       OK

echo [3/4] Compilando o executavel com PyInstaller...
if exist "dist\OrderFlow" rmdir /s /q "dist\OrderFlow"
if exist "build" rmdir /s /q "build"

py -m PyInstaller coupa_framework.spec --noconfirm --clean
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha na compilacao. Veja os erros acima.
    pause
    exit /b 1
)
echo       OK

echo       Removendo apenas browsers baixados do Playwright (usa Edge instalado)...
if exist "dist\OrderFlow\_internal\playwright\driver\package\.local-browsers" (
    rmdir /s /q "dist\OrderFlow\_internal\playwright\driver\package\.local-browsers"
)
echo       Mantendo o driver do Playwright (necessario para controlar o Edge).

echo       Removendo traducoes desnecessarias do PyQt6...
if exist "dist\OrderFlow\_internal\PyQt6\Qt6\translations" (
    rmdir /s /q "dist\OrderFlow\_internal\PyQt6\Qt6\translations"
)
echo       Removendo plugins Qt6 nao utilizados...
if exist "dist\OrderFlow\_internal\PyQt6\Qt6\plugins\sqldrivers" (
    rmdir /s /q "dist\OrderFlow\_internal\PyQt6\Qt6\plugins\sqldrivers"
)
rem NAO apagar a pasta imageformats inteira: e o plugin qico.dll dentro dela
rem que o Qt usa para decodificar .ico em tempo de execucao (ver
rem app.setWindowIcon em main.py) - sem ele, QIcon(icon.ico) carrega vazio e
rem a barra de titulo fica sem icone. PNG ja vem embutido no proprio Qt (sem
rem precisar de plugin), entao so o qico.dll precisa ficar; o resto pode
rem seguir sendo removido.
if exist "dist\OrderFlow\_internal\PyQt6\Qt6\plugins\imageformats" (
    for %%F in ("dist\OrderFlow\_internal\PyQt6\Qt6\plugins\imageformats\*.dll") do (
        if /i not "%%~nxF"=="qico.dll" del /q "%%F"
    )
)
echo       OK

echo [4/4] Gerando instalador com Inno Setup...

set "INNO="
for %%P in (
    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) do (
    if not defined INNO if exist %%P set "INNO=%%~P"
)

if defined INNO (
    if not exist "installer_output" mkdir "installer_output"
    "%INNO%" installer.iss
    set "ISCC_EXIT=!ERRORLEVEL!"
    if not "!ISCC_EXIT!"=="0" (
        echo [ERRO] Falha ao gerar o instalador com Inno Setup.
        pause
        exit /b 1
    )
    echo       OK

    echo.
    echo ============================================================
    echo  SUCESSO! Instalador gerado em: installer_output\
    echo ============================================================
) else (
    echo.
    echo [AVISO] Inno Setup nao encontrado.
    echo O executavel foi gerado em: dist\OrderFlow\OrderFlow.exe
    echo.
    echo Para gerar o instalador .exe:
    echo   1. Baixe o Inno Setup em: https://jrsoftware.org/isdl.php
    echo   2. Instale e execute novamente este script.
    echo.
    echo ============================================================
    echo  Build concluido sem instalador. EXE em: dist\OrderFlow\
    echo ============================================================
)

pause
