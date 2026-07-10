@echo off
setlocal

cd /d C:\Apps\RPAControlCenter

if not exist .venv\Scripts\python.exe (
    echo No se encontro el entorno virtual en C:\Apps\RPAControlCenter\.venv
    exit /b 1
)

set APP_ENV=production

.venv\Scripts\python.exe -u serve_waitress.py

endlocal