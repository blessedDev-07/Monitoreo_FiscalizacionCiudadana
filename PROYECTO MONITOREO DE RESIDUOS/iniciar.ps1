# Levanta TODO el sistema con un solo comando:  .\iniciar.ps1
# Requisitos: Python 3.11+ y Node.js 20+ instalados.
$ErrorActionPreference = "Stop"
$raiz  = $PSScriptRoot
$back  = Join-Path $raiz "backend"
$front = Join-Path $raiz "frontend"
$py    = Join-Path $back "venv\Scripts\python.exe"

Write-Host "==> 1/4 Entorno virtual" -ForegroundColor Green
if (-not (Test-Path $py)) { python -m venv (Join-Path $back "venv") }
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r (Join-Path $back "requirements.txt")

Write-Host "==> 2/4 Base de datos y datos de ejemplo" -ForegroundColor Green
Push-Location $back
& $py manage.py migrate
& $py manage.py cargar_datos
Pop-Location

Write-Host "==> 3/4 Dependencias de Angular" -ForegroundColor Green
if (-not (Test-Path (Join-Path $front "node_modules"))) {
    Push-Location $front; npm install; Pop-Location
}

Write-Host "==> 4/4 Iniciando servidores (3 ventanas)" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$back'; & '$py' manage.py runserver 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$back'; & '$py' manage.py simular_gps"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$front'; npm start"

Write-Host ""
Write-Host "API Django : http://localhost:8000/api/" -ForegroundColor Cyan
Write-Host "Admin      : http://localhost:8000/admin/  (admin / admin123)" -ForegroundColor Cyan
Write-Host "Angular    : http://localhost:4200  (se abre solo en unos segundos)" -ForegroundColor Cyan
