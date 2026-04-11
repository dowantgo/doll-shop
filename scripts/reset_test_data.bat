@echo off
setlocal

if not exist "%~dp0..\backend\venv\Scripts\python.exe" (
  echo Backend venv not found: backend\venv
  exit /b 1
)

pushd "%~dp0..\backend"

echo [1/3] Resetting database schema...
call venv\Scripts\python.exe manage.py flush --no-input
if errorlevel 1 (
  popd
  echo Database reset failed. Please ensure MySQL is started and backend\.env is correct.
  exit /b 1
)

echo [2/3] Re-running migrations...
call venv\Scripts\python.exe manage.py migrate
if errorlevel 1 (
  popd
  echo Django migrate failed.
  exit /b 1
)

echo [3/3] Rebuilding seed data...
call venv\Scripts\python.exe init_data_runner.py
if errorlevel 1 (
  popd
  echo Seed data initialization failed.
  exit /b 1
)

popd

echo.
echo Test data reset complete.
echo Suggested test accounts:
echo   admin / admin123
echo   user1 / user123

endlocal

