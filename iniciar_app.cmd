@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto folder_error

set "RACING_PYTHON="
set "RACING_PYTHON_ARGS="
set "RACING_BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%RACING_BUNDLED%" goto try_py
"%RACING_BUNDLED%" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto try_py
set "RACING_PYTHON=%RACING_BUNDLED%"
goto run

:try_py
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto try_python
set "RACING_PYTHON=py"
set "RACING_PYTHON_ARGS=-3"
goto run

:try_python
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto python_error
set "RACING_PYTHON=python"

:run
echo Preparando el informe. La primera vez se descargan los datos.
echo Version actual: demo de Espana-Inglaterra, Eurocopa 2024.
echo El analisis del Racing de esta temporada sigue pendiente de datos.
echo.
"%RACING_PYTHON%" %RACING_PYTHON_ARGS% -m racing_analysis demo
if errorlevel 1 goto run_error
if not exist "%~dp0output\informe.html" goto run_error
start "" "%~dp0output\informe.html"
if errorlevel 1 goto open_error
exit /b 0

:folder_error
echo No se puede abrir la carpeta del proyecto.
goto failed

:python_error
echo No se encuentra Python 3.10 o superior.
echo Instala Python desde https://www.python.org/downloads/windows/ y vuelve a abrir este archivo.
goto failed

:run_error
echo.
echo No se ha podido generar el informe. Copia el error que aparece arriba.
goto failed

:open_error
echo El informe se ha generado. Puedes abrirlo manualmente:
echo "%~dp0output\informe.html"
goto failed

:failed
echo.
pause
exit /b 1
