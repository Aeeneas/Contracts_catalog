@echo off
chcp 65001 > nul
set PROJECT_ROOT=%~dp0

echo [1/2] Запуск Backend (FastAPI)...
start "Backend - FastAPI" cmd /k "cd /d %PROJECT_ROOT%backend && venv\Scripts\activate && python main.py"

echo [2/2] Запуск Frontend (React)...
start "Frontend - React" cmd /k "cd /d %PROJECT_ROOT%frontend && npm start"

echo.
echo ======================================================
echo Проект запускается в двух отдельных окнах!
echo Бэкенд: http://127.0.0.1:8000
echo Фронтенд: http://localhost:3000
echo ======================================================
echo.
pause