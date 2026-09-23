@echo off
title JMB PERFORMANCE - SERVIDOR PERMANENTE LOCAL
cls
echo ==================================================
echo       INICIANDO JMB PERFORMANCE PERMANENTE
echo ==================================================
echo.
echo Endereco Local: http://localhost:8080
echo.
cd /d "C:\Users\Hiago JMB\.gemini\antigravity\scratch\jmb-performance"

start "" "http://localhost:8080"

echo Iniciando servidor principal...
"C:\Users\Hiago JMB\.local\bin\uv.exe" run --with fastapi --with uvicorn --with sqlalchemy --with pandas --with openpyxl python run.py
