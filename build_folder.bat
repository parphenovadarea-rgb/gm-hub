@echo off
rem Build GameMasterHub into the folder dist\GameMasterHub (starts in 0.3-0.8 s).
rem Run from the project root. Needs the virtual environment .venv.
rem The folder _internal must stay next to GameMasterHub.exe.

if not exist ".venv\Scripts\python.exe" goto no_venv

.venv\Scripts\python -m PyInstaller --noconfirm --onedir --windowed --name GameMasterHub --collect-submodules gm_hub --exclude-module PySide6.QtNetwork --add-data "gm_hub\db\schema.sql;gm_hub/db" main.py
if errorlevel 1 goto failed

rem Software OpenGL (20 MB) is not needed by the program windows.
del /q "dist\GameMasterHub\_internal\PySide6\opengl32sw.dll" 2>nul

echo.
echo Done: dist\GameMasterHub\GameMasterHub.exe
exit /b 0

:no_venv
echo No virtual environment .venv. Create it first:
echo     py -m venv .venv
echo     .venv\Scripts\pip install -r requirements-dev.txt
exit /b 1

:failed
echo Build failed.
exit /b 1
