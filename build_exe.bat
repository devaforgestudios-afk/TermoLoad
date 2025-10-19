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

echo Building executable with PyInstaller...
echo This may take a few minutes...
echo.

pyinstaller build_exe.spec --clean

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
