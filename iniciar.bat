@echo off
cd /d "%~dp0"
title Jaguar POS
echo Abriendo el navegador...
start "" "http://127.0.0.1:8000/"
echo Iniciando servidor Django...
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
