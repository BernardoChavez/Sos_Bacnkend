@echo off
echo Iniciando SOS Automotriz Backend...
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
pause
