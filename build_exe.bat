@echo off
echo ========================================
echo Building TermoLoad Executable
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    echo.
)

echo Building executable with PyInstaller (mode: %1, windowed: %2)...
echo This may take a few minutes...
echo.

REM Default to onedir (faster startup) and console mode for better performance
set MODE=%1
set WINDOWED=%2
if "%MODE%"=="" set MODE=onedir
if "%WINDOWED%"=="" set WINDOWED=console

REM Build args
set PYI_ARGS=--clean
if "%MODE%"=="onefile" (
    set PYI_ARGS=%PYI_ARGS% --onefile
)
if "%WINDOWED%"=="noconsole" (
    set PYI_ARGS=%PYI_ARGS% --noconsole
)

echo Running: pyinstaller %PYI_ARGS% build_exe.spec
pyinstaller %PYI_ARGS% build_exe.spec

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
echo The executable can be found in: dist\TermoLoad.exe
echo.
echo You can now run the application by executing:
echo   dist\TermoLoad.exe
echo.
pause
