# Script para iniciar el entorno de desarrollo local de IMA Agent (FastAPI + React + PostgreSQL)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIANDO IMA AGENT (FastAPI + React + PostgreSQL)     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verificar si el contenedor de PostgreSQL esta corriendo
$pgRunning = docker ps --filter "name=imaagent_postgres" --format "{{.Names}}"
if (-not $pgRunning) {
    Write-Host "[1/3] Iniciando contenedor PostgreSQL..." -ForegroundColor Yellow
    docker start imaagent_postgres
    if ($LASTEXITCODE -ne 0) {
        docker run -d --name imaagent_postgres -e POSTGRES_DB=imaagent_db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine
    }
} else {
    Write-Host "[1/3] PostgreSQL ya esta activo en el puerto 5432." -ForegroundColor Green
}

# 2. Iniciar Backend FastAPI en una ventana independiente
Write-Host "[2/3] Levantando Backend FastAPI en http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; ..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

# 3. Iniciar Frontend Vite en una ventana independiente
Write-Host "[3/3] Levantando Frontend Vite en http://127.0.0.1:5174..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm.cmd run dev -- --host 127.0.0.1 --port 5174"

Write-Host ""
Write-Host "Todo listo. Abre tu navegador en: http://127.0.0.1:5174" -ForegroundColor Green
Write-Host "Usuario: admin | Clave: Ima2026!" -ForegroundColor Green
