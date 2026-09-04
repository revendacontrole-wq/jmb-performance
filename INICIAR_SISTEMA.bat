@echo off
title JMB PERFORMANCE - SERVIDOR PERMANENTE 24/7
cls
echo ==================================================
echo       INICIANDO JMB PERFORMANCE PERMANENTE
echo ==================================================
echo.
echo Endereco Local: http://localhost:8080
echo.
cd /d "C:\Users\Hiago JMB\.gemini\antigravity\scratch\jmb-performance"

start /b "CloudflarePermanentTunnel" "cloudflared.exe" tunnel run --token eyJhIjoiMmY0NzhiNDYwNGE0ZTJmNTRlMmNkZDRmZjIzNDNiYjgiLCJ0IjoiOGJkMzI4NTctODhiNy00MjdkLTllMWUtYWFlNmY4MjUzMDRkIiwicyI6Ik5UaG1NR013WWpjdFlqSTNPQzAwWkRsa0xUbG1aVGt0Wm1Nek9EbGxZak0zTnpGayJ9

echo Iniciando servidor principal...
"C:\Users\Hiago JMB\.local\bin\uv.exe" run --with fastapi --with uvicorn --with sqlalchemy --with pandas --with openpyxl python run.py
