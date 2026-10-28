# Sistema de Monitoreo de Residuos Sólidos – Amarilis

Backend: Django + Django REST Framework · Frontend: Angular 18 + Leaflet · BD: SQLite

## Arranque automático (Windows PowerShell)
```powershell
cd "C:\Users\User\Desktop\PROYECTO MONITOREO DE RESIDUOS"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\iniciar.ps1
```

## Arranque manual
```powershell
# Terminal 1 – API
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_datos
python manage.py runserver

# Terminal 2 – simulador GPS (camiones en el mapa)
cd backend ; .\venv\Scripts\Activate.ps1 ; python manage.py simular_gps

# Terminal 3 – Angular
cd frontend
npm install
npm start
```

## Pruebas
```powershell
cd backend ; .\venv\Scripts\Activate.ps1
pytest              # o: pytest --cov=residuos
```

## Endpoints principales
| Método | URL | Descripción |
|---|---|---|
| GET/POST | /api/incidencias/ | Listar / reportar incidencias |
| POST | /api/incidencias/{id}/cambiar-estado/ | PENDIENTE → EN_PROCESO → RESUELTA |
| GET | /api/camiones/ · /api/camiones/posiciones-actuales/ | Flota y GPS actual |
| POST | /api/posiciones/ | La app del operador envía coordenadas |
| GET | /api/rutas/ · /api/horarios/ · /api/puntos-ruta/ | Rutas y horarios |
| POST | /api/recorridos/iniciar/ · /api/recorridos/{id}/finalizar/ | Fiscalización |
| GET | /api/estadisticas/resumen/ | Datos del panel web |
