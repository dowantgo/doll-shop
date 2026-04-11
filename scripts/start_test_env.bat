@echo off
setlocal

echo [1/6] Checking backend virtual environment...
if not exist "%~dp0..\backend\venv\Scripts\python.exe" (
  echo Backend venv not found: backend\venv
  echo Please create it first:
  echo   cd backend
  echo   python -m venv venv
  exit /b 1
)

echo [2/6] Checking backend test env file...
if not exist "%~dp0..\backend\.env" (
  if exist "%~dp0..\backend\.env.test.example" (
    copy /Y "%~dp0..\backend\.env.test.example" "%~dp0..\backend\.env" >nul
    echo Created backend\.env from .env.test.example
  ) else (
    echo backend\.env not found, and .env.test.example is missing.
    exit /b 1
  )
)

echo [3/6] Installing frontend dependencies if needed...
if not exist "%~dp0..\frontend\node_modules" (
  pushd "%~dp0..\frontend"
  call npm install
  if errorlevel 1 (
    popd
    echo npm install failed.
    exit /b 1
  )
  popd
)

echo [4/6] Running backend migrations...
pushd "%~dp0..\backend"
call venv\Scripts\python.exe manage.py migrate
if errorlevel 1 (
  popd
  echo Django migrate failed. Please ensure MySQL and Redis are started, and backend\.env is correct.
  exit /b 1
)

echo [5/6] Initializing test data...
call venv\Scripts\python.exe init_data_runner.py
if errorlevel 1 (
  popd
  echo Test data initialization failed.
  exit /b 1
)
popd

echo [6/6] Starting backend and frontend in new windows...
start "shop-backend-test" powershell -NoExit -Command "Set-Location '%~dp0..\backend'; .\venv\Scripts\Activate.ps1; python manage.py runserver 0.0.0.0:8000"
start "shop-frontend-test" powershell -NoExit -Command "Set-Location '%~dp0..\frontend'; npm run dev -- --host 0.0.0.0 --port 5173"

echo.
echo Test environment is starting...
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000
echo.
echo Suggested test accounts:
echo   admin / admin123
echo   user1 / user123

endlocal

