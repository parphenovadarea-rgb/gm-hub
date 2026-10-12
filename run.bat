@echo off
rem Run the program from source strictly inside the virtual environment .venv.

if not exist ".venv\Scripts\python.exe" goto no_venv

.venv\Scripts\python main.py
exit /b %errorlevel%

:no_venv
echo No virtual environment .venv. Create it first:
echo     py -m venv .venv
echo     .venv\Scripts\pip install -r requirements.txt
exit /b 1
