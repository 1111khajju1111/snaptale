@echo off
echo Cleaning cache and build artifacts...
for /d /r . %%d in (__pycache__) do @if exist %%d rd /s /q %%d
for /d /r . %%d in (.pytest_cache) do @if exist %%d rd /s /q %%d
del /s /q *.pyc >nul 2>&1
del /s /q *.pyo >nul 2>&1
if exist backend\test_suite.db del /q backend\test_suite.db
if exist test_suite.db del /q test_suite.db
if exist mobile\flutter_app\.dart_tool rd /s /q mobile\flutter_app\.dart_tool
if exist mobile\flutter_app\build rd /s /q mobile\flutter_app\build
echo Done!
