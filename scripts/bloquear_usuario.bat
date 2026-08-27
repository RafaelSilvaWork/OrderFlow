@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1"=="" (
    set /p "USERNAME=Username do Windows da pessoa: "
    set /p "MODO=Bloquear ou desbloquear? [B/d]: "
) else (
    set "USERNAME=%~1"
    set "MODO=%~2"
)

if "%USERNAME%"=="" (
    echo Username nao pode ser vazio.
    pause
    exit /b 1
)

if /i "%MODO%"=="d" (
    py -3 "%SCRIPT_DIR%bloquear_usuario.py" "%USERNAME%" --desbloquear
) else (
    py -3 "%SCRIPT_DIR%bloquear_usuario.py" "%USERNAME%"
)

echo.
pause
