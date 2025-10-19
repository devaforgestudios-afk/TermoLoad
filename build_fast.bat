@echo off
REM build_fast.bat - build TermoLoad using PyInstaller without .spec for flexible modes
REM Usage: build_fast.bat [onefile|onedir] [console|noconsole]

set MODE=%1
set WINDOWED=%2
if "%MODE%"=="" set MODE=onedir
if "%WINDOWED%"=="" set WINDOWED=console

echo ========================================
echo Fast build script - mode=%MODE% windowed=%WINDOWED%
echo ========================================

echo Checking PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

set PYI_FLAGS=--clean
if "%MODE%"=="onefile" (
    set PYI_FLAGS=%PYI_FLAGS% --onefile
) else (
    REM default is onedir (no --onefile)
)
if "%WINDOWED%"=="noconsole" (
    set PYI_FLAGS=%PYI_FLAGS% --noconsole
)

echo Running: pyinstaller %PYI_FLAGS% --name TermoLoad app.py
pyinstaller %PYI_FLAGS% --name TermoLoad app.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build SUCCESSFUL!
echo ========================================
echo.
echo Outputs:
if exist dist\TermoLoad (
    dir dist\TermoLoad
) else (
    dir dist
)

echo.
echo You can run the app from the dist folder.
pause
