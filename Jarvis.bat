@echo off
cd /d "%~dp0"

set "address=192.168.29.111:5555"

:: ── Step 1: Relaunch as admin if not already ──────────────────────────────
>nul 2>&1 net session
if %errorlevel% neq 0 (
    echo Requesting admin privileges...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\admin.vbs"
    echo UAC.ShellExecute "cmd.exe", "/k cd /d ""%~dp0"" && ""%~f0""", "", "runas", 1 >> "%temp%\admin.vbs"
    "%temp%\admin.vbs"
    del "%temp%\admin.vbs"
    exit /b
)

echo Running as admin...
echo.

:: ── Step 2: List connected devices ────────────────────────────────────────
echo [*] Checking connected ADB devices...
adb devices
echo.

:: ── Step 3: Check if target device already connected wirelessly ────────────
adb devices | findstr /i "%address%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Target device %address% already connected. Skipping tcpip step.
    goto launch
)

:: ── Step 4: Find USB-only device serial (no colon in serial = USB) ─────────
echo [*] Attempting to set ADB to TCP/IP mode on port 5555...
setlocal enabledelayedexpansion
set "usb_serial="
for /f "skip=1 tokens=1,2" %%i in ('adb devices') do (
    if "%%j"=="device" (
        echo %%i | findstr ":" >nul 2>&1
        if !errorlevel! neq 0 set "usb_serial=%%i"
    )
)

if defined usb_serial (
    echo [*] Found USB device: !usb_serial!
    adb -s !usb_serial! tcpip 5555
    if !errorlevel! neq 0 (
        echo.
        echo [!] Error: Could not set TCP/IP mode on !usb_serial!.
        echo     Make sure USB Debugging is enabled on your device.
        echo.
        echo     Connect your device now then press Enter to retry,
        echo     or just press Enter to continue anyway.
        echo.
        pause >nul
        echo [*] Retrying...
        adb -s !usb_serial! tcpip 5555
        if !errorlevel! neq 0 (echo [!] Still failed. Continuing anyway...) else (echo [+] TCP/IP mode set!)
    ) else (
        echo [+] TCP/IP mode set on !usb_serial!
    )
) else (
    echo [!] No USB device found.
    echo.
    echo     Connect your device via USB then press Enter to retry,
    echo     or just press Enter to continue anyway.
    echo.
    pause >nul
    echo [*] Retrying...
    adb tcpip 5555
    if errorlevel 1 (echo [!] Still failed. Continuing anyway...) else (echo [+] TCP/IP mode set!)
)

echo.

:: ── Step 5: Connect to target device over Wi-Fi ───────────────────────────
:launch
echo [*] Connecting to %address%...
adb connect %address%
echo.

:: ── Step 6: Run main script ───────────────────────────────────────────────
echo [*] Launching main.py...
python main.py

pause