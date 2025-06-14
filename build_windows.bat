@echo off
REM ====================================================================
REM GameDrop Windows Build Script
REM ====================================================================
REM This script builds the GameDrop application for Windows:
REM 1. Creates a one-folder distribution using PyInstaller
REM 2. Creates an installer using Inno Setup
REM ====================================================================

echo GameDrop Windows Build Process
echo ==============================

REM Check if Python and pip are available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not found in PATH
    exit /b 1
)

REM Check Python version
python --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: Could not determine Python version
    exit /b 1
)

REM Ensure PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install PyInstaller
        exit /b 1
    )
)

REM Ensure all dependencies are installed
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo WARNING: Some dependencies may not have installed correctly
    echo The build will continue, but you might encounter issues
)

REM Clean previous build directories
echo Cleaning previous build...
if exist build\GameDrop_Windows rmdir /s /q build\GameDrop_Windows
if exist dist\GameDrop rmdir /s /q dist\GameDrop

REM Create required directories
if not exist installer\windows\output mkdir installer\windows\output

REM Build the application using PyInstaller with the Windows spec
echo Building application with PyInstaller...
pyinstaller GameDrop_Windows.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo PyInstaller build completed successfully.
echo Executable created at: dist\GameDrop\GameDrop.exe

REM Check if the output executable exists
if not exist dist\GameDrop\GameDrop.exe (
    echo ERROR: Build output not found
    exit /b 1
)

REM Check if Inno Setup Compiler (ISCC) is available
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "INNO_PATH_ALT=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%INNO_PATH%" (
    set "ISCC_EXE=%INNO_PATH%"
    goto BuildInstaller
) else if exist "%INNO_PATH_ALT%" (
    set "ISCC_EXE=%INNO_PATH_ALT%"
    goto BuildInstaller
) else (
    echo WARNING: Inno Setup Compiler (ISCC) not found.
    echo You need to install Inno Setup from https://jrsoftware.org/isdl.php
    echo Then manually run: ISCC.exe installer\windows\gamedrop.iss
    echo Build process completed without creating an installer.
    echo You can find the application in dist\GameDrop\
    exit /b 0
)

:BuildInstaller
echo Building installer with Inno Setup...
echo Using Inno Setup at: "%ISCC_EXE%"
call "%ISCC_EXE%" "installer\windows\gamedrop.iss"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Inno Setup compilation failed with error code: %ERRORLEVEL%
    exit /b 1
) else (
    echo Installer created successfully!
    echo Installer: installer\windows\output\GameDrop_Setup.exe
)

echo ISCC_EXE: %ISCC_EXE%

echo Build process completed.
echo.
echo Application: dist\GameDrop\GameDrop.exe
echo Installer: installer\windows\output\GameDrop_Setup.exe
echo.
echo To test the application, run: dist\GameDrop\GameDrop.exe
echo To install the application, run: installer\windows\output\GameDrop_Setup.exe

exit /b 0
