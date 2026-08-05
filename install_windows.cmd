@echo off
setlocal enabledelayedexpansion

rem Installs the Kitsu Nuke Plugin into Nuke's user plugin folder.
rem
rem Usage: install_windows.cmd [custom .nuke folder]
rem   Run with no arguments to install to the standard location
rem   (%%USERPROFILE%%\.nuke), which every Nuke version scans at startup.
rem   If you keep your Nuke setup elsewhere (a folder on NUKE_PATH), pass
rem   that folder as an argument to this script instead.
rem
rem Two things are installed: the kitsu_nuke_plugin folder itself, and a
rem two-line entry in that folder's init.py telling Nuke to load it. Nuke
rem only auto-runs init.py/menu.py for folders that are ON its plugin
rem path, and it does not look inside sub-folders on its own, so the
rem pluginAddPath line below is what actually activates the plugin.

set "SCRIPT_DIR=%~dp0"
set "SOURCE=%SCRIPT_DIR%kitsu_nuke_plugin"

if "%~1"=="" (
    set "TARGET=%USERPROFILE%\.nuke"
) else (
    set "TARGET=%~1"
)

echo Installing Kitsu Nuke Plugin
echo   From: %SOURCE%
echo   To:   %TARGET%\kitsu_nuke_plugin
echo.

if not exist "%SOURCE%\menu.py" (
    echo ERROR: %SOURCE% not found or incomplete.
    echo Run this script from the repository root, or check your checkout.
    exit /b 1
)

if not exist "%TARGET%" (
    mkdir "%TARGET%"
    if errorlevel 1 (
        echo ERROR: Could not create %TARGET%
        exit /b 1
    )
)

rem Remove any previous install of this plugin's own folder first, for a
rem clean, idempotent install that never leaves stale files from an older
rem version behind.
if exist "%TARGET%\kitsu_nuke_plugin" (
    rmdir /s /q "%TARGET%\kitsu_nuke_plugin"
)

robocopy "%SOURCE%" "%TARGET%\kitsu_nuke_plugin" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS >nul
if errorlevel 8 (
    echo ERROR: Could not copy the plugin folder.
    exit /b 1
)

set "INIT=%TARGET%\init.py"
findstr /c:"kitsu-nuke-plugin" "%INIT%" >nul 2>&1
if errorlevel 1 (
    rem Appended, never rewritten: this init.py is the user's own file and
    rem may well already have other studio setup in it.
    echo.>>"%INIT%"
    echo # kitsu-nuke-plugin: added by its installer>>"%INIT%"
    echo import nuke>>"%INIT%"
    echo nuke.pluginAddPath^("./kitsu_nuke_plugin"^)>>"%INIT%"
    echo   Registered the plugin in %INIT%
) else (
    echo   %INIT% already registers the plugin - left as is.
)

echo.
echo Done. Restart Nuke - a "Kitsu" menu appears in the menu bar, with
echo "Open Kitsu Panel" and "Publish Capture". The panel is also in the
echo pane menu of any pane, listed as "Kitsu".
pause
endlocal
