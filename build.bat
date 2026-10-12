@echo off
rem Build GameMasterHub as ONE file: dist\GameMasterHub.exe (about 36 MB).
rem Run from the project root. Needs the virtual environment .venv
rem (py -m venv .venv, then .venv\Scripts\pip install -r requirements-dev.txt).
rem The file unpacks itself into a temp folder on start, so it starts in about 1 s.
rem If that is too slow on some computer, use build_folder.bat instead.

if not exist ".venv\Scripts\python.exe" goto no_venv

.venv\Scripts\python -m PyInstaller --noconfirm --onefile --windowed --name GameMasterHub --collect-submodules gm_hub --exclude-module PySide6.QtNetwork --add-data "gm_hub\db\schema.sql;gm_hub/db" main.py
if errorlevel 1 goto failed

echo.
echo Done: dist\GameMasterHub.exe
echo On first start it creates gm_hub.db, settings.json and gm_hub.log next to the file.
exit /b 0

:no_venv
echo No virtual environment .venv. Create it first:
echo     py -m venv .venv
echo     .venv\Scripts\pip install -r requirements-dev.txt
exit /b 1

:failed
echo Build failed.
exit /b 1
