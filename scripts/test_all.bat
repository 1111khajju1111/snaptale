@echo off
echo ========================================================
echo Running Complete SnapTale Test Suite
echo ========================================================

echo [1/3] Running FastAPI Backend Tests (pytest)...
cd backend
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Backend tests failed!
    exit /b %ERRORLEVEL%
)
cd ..

echo.
echo [2/3] Running Flutter Mobile Tests...
cd mobile/flutter_app
call flutter test
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Flutter tests failed!
    exit /b %ERRORLEVEL%
)
cd ..\..

echo.
echo [3/3] Verifying Next.js Web Build...
cd web
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Next.js build failed!
    exit /b %ERRORLEVEL%
)
cd ..

echo.
echo ========================================================
echo ALL SNAPTALE VERIFICATION TESTS PASSED SUCCESSFULLY!
echo ========================================================