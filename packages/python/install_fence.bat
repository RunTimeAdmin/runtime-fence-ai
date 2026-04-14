@echo off
echo.
echo ========================================
echo   RUNTIME FENCE - ONE-CLICK INSTALLER
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    echo Download from: https://python.org/downloads
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install requests psutil pystray pillow --quiet

echo [2/4] Creating start script...
echo @echo off > "%USERPROFILE%\Desktop\Runtime Fence.bat"
echo cd /d "%~dp0" >> "%USERPROFILE%\Desktop\Runtime Fence.bat"
echo python fence_tray.py >> "%USERPROFILE%\Desktop\Runtime Fence.bat"

echo [3/4] Creating startup shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\shortcut.vbs"
echo sLinkFile = oWS.SpecialFolders("Startup") ^& "\Runtime Fence.lnk" >> "%TEMP%\shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\shortcut.vbs"
echo oLink.TargetPath = "%~dp0fence_tray.py" >> "%TEMP%\shortcut.vbs"
echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\shortcut.vbs"
echo oLink.Save >> "%TEMP%\shortcut.vbs"
cscript //nologo "%TEMP%\shortcut.vbs"
del "%TEMP%\shortcut.vbs"

echo [4/4] Installation complete!
echo.
echo ========================================
echo   INSTALLATION SUCCESSFUL
echo ========================================
echo.
echo A shortcut has been added to your Desktop.
echo Runtime Fence will auto-start with Windows.
echo.
echo To start now, double-click "Runtime Fence" on your Desktop
echo or run: python fence_tray.py
echo.
pause
